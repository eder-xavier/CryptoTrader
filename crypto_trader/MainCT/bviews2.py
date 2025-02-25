import requests
from django.shortcuts import render
from .models import BuscaHistorico
from sklearn.neighbors import NearestNeighbors
import numpy as np

def get_criptos_da_api(query):
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 100,
        "page": 1,
        "sparkline": False,
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        criptos = [
            {
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
    except requests.exceptions.RequestException as e:
        print(f"Erro na API: {e}")
        return [
            {"nome": "Bitcoin", "simbolo": "BTC", "preco": 60000, "market_cap": 1200000000000, "volume_24h": 30000000000},
            {"nome": "Ethereum", "simbolo": "ETH", "preco": 3000, "market_cap": 360000000000, "volume_24h": 15000000000},
        ]

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
    # Pegando o histórico de buscas
    historico = BuscaHistorico.objects.all().order_by('-data')[:10]
    recomendados = []
    
    if historico:
        recomendados = gerar_recomendacoes(historico)
    
    return render(request, 'MainCT/recomendacoes.html', {
        'recomendados': recomendados,
    })

def gerar_recomendacoes(historico):
    # Extraindo features do histórico
    features_historico = []
    criptos_historico = []
    for busca in historico:
        for item in busca.resultados:
            features_historico.append([item['preco'], item['market_cap'], item['volume_24h']])
            criptos_historico.append(item)
    
    if not features_historico:
        return []

    # Pegando todas as criptos disponíveis na API para recomendar
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {"vs_currency": "usd", "order": "market_cap_desc", "per_page": 100, "page": 1}
    response = requests.get(url, params=params)
    data = response.json()
    criptos_disponiveis = [
        {
            "nome": item["name"],
            "simbolo": item["symbol"].upper(),
            "preco": float(item["current_price"]),
            "market_cap": float(item["market_cap"]),
            "volume_24h": float(item["total_volume"])
        }
        for item in data
    ]
    
    features_disponiveis = [[c['preco'], c['market_cap'], c['volume_24h']] for c in criptos_disponiveis]
    
    # Treinando o modelo com o histórico
    X = np.array(features_historico)
    nbrs = NearestNeighbors(n_neighbors=5, algorithm='ball_tree').fit(np.array(features_disponiveis))
    
    # Usando a última busca como referência
    ultima_busca = features_historico[-1]
    distances, indices = nbrs.kneighbors([ultima_busca])
    
    # Selecionando as criptos recomendadas
    recomendados = [criptos_disponiveis[i] for i in indices[0] if criptos_disponiveis[i] not in criptos_historico]
    return recomendados[:5]  # Limitando a 5 recomendações