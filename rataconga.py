import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Permite que o seu site (Frontend) consiga conversar com esta API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, substitua pelo link real do seu site
    allow_methods=["*"],
    allow_headers=["*"],
)

# API pública do INMET para avisos meteorológicos ativos
INMET_API_URL = "https://apiprevmet3.inmet.gov.br/avisos/ativos"


ESTADOS = {
    "AC": "Acre",
    "AL": "Alagoas",
    "AP": "Amapá",
    "AM": "Amazonas",
    "BA": "Bahia",
    "CE": "Ceará",
    "DF": "Distrito Federal",
    "ES": "Espírito Santo",    
    "GO": "Goiás",
    "MA": "Maranhão",
    "MT": "Mato Grosso",
    "MS": "Mato Grosso do Sul",
    "MG": "Minas Gerais",
    "PA": "Pará",
    "PB": "Paraíba",
    "PR": "Paraná",
    "PE": "Pernambuco",
    "PI": "Piauí",
    "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte",
    "RS": "Rio Grande do Sul",
    "RO": "Rondônia",
    "RR": "Roraima",
    "SC": "Santa Catarina",
    "SP": "São Paulo",
    "SE": "Sergipe",
    "TO": "Tocantins",
}

@app.get("/alerta-climatico")
def verificar_clima_estado(estado: str):
    estado_busca = estado.strip().upper()
    nome_estado = ESTADOS.get(estado_busca)
    if nome_estado is None:
        raise HTTPException(
            status_code=400,
            detail="Informe a sigla válida de um estado brasileiro.",
        )

    try:
        resposta = requests.get(
            INMET_API_URL,
            timeout=10,
        )
        resposta.raise_for_status()
        dados = resposta.json()
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail="Erro ao conectar com o serviço meteorológico.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="Resposta inválida do serviço meteorológico.") from exc

    if not isinstance(dados, dict) or not all(
        isinstance(dados.get(categoria), list) for categoria in ("hoje", "futuro")
    ):
        raise HTTPException(status_code=502, detail="Resposta inválida do serviço meteorológico.")

    alertas_encontrados = []
    for aviso in dados["hoje"] + dados["futuro"]:
        if not isinstance(aviso, dict):
            raise HTTPException(status_code=502, detail="Resposta inválida do serviço meteorológico.")
        estados_aviso = aviso.get("estados", "")
        if isinstance(estados_aviso, str) and nome_estado.casefold() in {
            nome.strip().casefold() for nome in estados_aviso.split(",")
        }:
            riscos = aviso.get("riscos", [])
            alertas_encontrados.append({
                "evento": aviso.get("descricao"),
                "severidade": aviso.get("severidade"),
                "inicio": aviso.get("inicio"),
                "fim": aviso.get("fim"),
                "descricao": " ".join(riscos) if isinstance(riscos, list) else ""
            })

    if alertas_encontrados:
        return {
            "estado": estado_busca,
            "tem_alerta_grande": True,
            "alertas": alertas_encontrados
        }
    
    return {
        "estado": estado_busca,
        "tem_alerta_grande": False,
        "mensagem": "Nenhum alerta climático ativo encontrado para este estado no momento."
    }
