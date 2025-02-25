import requests
import numpy as np
from django.shortcuts import render
from .models import BuscaHistorico
import tensorflow as tf
from datetime import datetime, timedelta
import time

def get_dados_historicos(cripto_id, dias=30):
    url = f"https://api.coingecko.com/api/v3/coins/{cripto_id}/market_chart"
    params = {
        "vs_currency": "usd",
        "days": dias,
        "interval": "daily",
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        precos = data["prices"]
        return [(p[1], p[1] * 1.02, p[1] * 0.98) for p in precos]
    except requests.exceptions.RequestException as e:
        print(f"Erro ao buscar histórico: {e}")
        time.sleep(2)  # Atraso para respeitar limite de requisições
        return [(60000, 61000, 59000)] * dias

def get_criptos_da_api(query):
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 100,
        "page": 1,
        "sparkline": False,
    }
    response = requests.get(url, params=params)
    data = response.json()
    criptos = [
        {
            "id": item["id"],
            "nome": item["name"],
            "simbolo": item["symbol"].upper(),
            "preco": float(item["current_price"]),
            "market_cap": float(item["market_cap"]),
            "volume_24h": float(item["total_volume"])
        }
        for item in data
        if query.lower() in item["name"].lower() or query.lower() in item["symbol"].lower()
    ]
    return criptos[:10]

def criar_modelo():
    model = tf.keras.models.Sequential([
        tf.keras.layers.Input(shape=(30, 3)),  # Corrigindo o aviso do Keras
        tf.keras.layers.LSTM(50, return_sequences=True),
        tf.keras.layers.LSTM(50),
        tf.keras.layers.Dense(25, activation='relu'),
        tf.keras.layers.Dense(1)
    ])
    model.compile(optimizer='adam', loss='mse')
    return model

def treinar_e_prever(historico_dados):
    X, y = [], []
    for dados in historico_dados:
        if len(dados) >= 30:
            for i in range(len(dados) - 30):
                X.append(dados[i:i+30])
                y.append(dados[i+30][0])
    if not X:
        return None
    
    X = np.array(X)
    y = np.array(y)
    
    model = criar_modelo()
    model.fit(X, y, epochs=10, batch_size=32, verbose=0)
    
    ultimo_periodo = np.array([historico_dados[-1][-30:]])
    previsao = model.predict(ultimo_periodo, verbose=0)[0][0]
    return previsao

def gerar_portfolio(historico):
    criptos_analisadas = {}
    for busca in historico:
        for cripto in busca.resultados:
            # Verificando se 'id' existe no dicionário
            if 'id' not in cripto:
                continue  # Pula se não houver 'id'
            cripto_id = cripto['id']
            if cripto_id not in criptos_analisadas:
                dados_historicos = get_dados_historicos(cripto_id)
                previsao = treinar_e_prever([dados_historicos])
                if previsao and previsao > cripto['preco']:
                    criptos_analisadas[cripto_id] = {
                        "nome": cripto["nome"],
                        "simbolo": cripto["simbolo"],
                        "preco_atual": cripto["preco"],
                        "previsao": previsao,
                        "tendencia": "Alta" if previsao > cripto["preco"] else "Baixa",
                        "lucro_potencial": previsao - cripto["preco"]
                    }
                time.sleep(2)  # Atraso para evitar erro 429
    
    portfolio = sorted(criptos_analisadas.values(), key=lambda x: x["lucro_potencial"], reverse=True)[:5]
    return portfolio

def index(request):
    return render(request, 'MainCT/index.html')

def buscar_criptos(request):
    query = request.GET.get('q', '')
    criptos = []
    if query:
        criptos = get_criptos_da_api(query)
        BuscaHistorico.objects.create(query=query, resultados=criptos)
    return render(request, 'MainCT/index.html', {'criptos': criptos})

def recomendacoes(request):
    historico = BuscaHistorico.objects.all().order_by('-data')[:10]
    recomendados = gerar_recomendacoes(historico) if historico else []
    return render(request, 'MainCT/recomendacoes.html', {'recomendados': recomendados})

def portfolio(request):
    historico = BuscaHistorico.objects.all().order_by('-data')[:10]
    portfolio_criptos = gerar_portfolio(historico) if historico else []
    return render(request, 'MainCT/portfolio.html', {'portfolio': portfolio_criptos})

def gerar_recomendacoes(historico):
    features_historico = []
    criptos_historico = []
    for busca in historico:
        for item in busca.resultados:
            features_historico.append([item['preco'], item['market_cap'], item['volume_24h']])
            criptos_historico.append(item)
    
    if not features_historico:
        return []

    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {"vs_currency": "usd", "order": "market_cap_desc", "per_page": 100, "page": 1}
    response = requests.get(url, params=params)
    data = response.json()
    criptos_disponiveis = [
        {"nome": item["name"], "simbolo": item["symbol"].upper(), "preco": float(item["current_price"]),
         "market_cap": float(item["market_cap"]), "volume_24h": float(item["total_volume"])}
        for item in data
    ]
    features_disponiveis = [[c['preco'], c['market_cap'], c['volume_24h']] for c in criptos_disponiveis]
    
    from sklearn.neighbors import NearestNeighbors
    X = np.array(features_historico)
    nbrs = NearestNeighbors(n_neighbors=5, algorithm='ball_tree').fit(np.array(features_disponiveis))
    ultima_busca = features_historico[-1]
    distances, indices = nbrs.kneighbors([ultima_busca])
    
    recomendados = [criptos_disponiveis[i] for i in indices[0] if criptos_disponiveis[i] not in criptos_historico]
    return recomendados[:5]