"""Gera dados.js (auditores com certificação vigente) para a página do Cadastro.

Fonte: aba "Publicação" da planilha Google de controle, publicada na Web como CSV
(Arquivo > Compartilhar > Publicar na Web > aba Publicação > CSV). Essa aba é gerada por
fórmula a partir da aba "Controle" e contém só as colunas públicas e só as linhas com
situação "Vigente". A situação e as observações nunca saem da planilha.

Uso:
  python3 ferramentas/gerar_dados.py --csv <URL ou caminho do CSV> [--mapa brazil-states.geojson]

Sem dependências externas (só a biblioteca padrão do Python).
Se houver qualquer erro nos dados, o script não grava nada e termina com código 1:
a versão publicada continua a anterior.
"""
import argparse
import csv
import datetime
import io
import json
import math
import re
import sys
import unicodedata
import urllib.request
from pathlib import Path

UF_NOME = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", "BA": "Bahia",
    "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás",
    "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul", "MG": "Minas Gerais",
    "PA": "Pará", "PB": "Paraíba", "PR": "Paraná", "PE": "Pernambuco", "PI": "Piauí",
    "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte", "RS": "Rio Grande do Sul",
    "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina", "SP": "São Paulo",
    "SE": "Sergipe", "TO": "Tocantins",
}
_PREP = {
    "AC": "do", "AL": "de", "AP": "do", "AM": "do", "BA": "da", "CE": "do", "ES": "do",
    "GO": "de", "MA": "do", "MT": "de", "MS": "de", "MG": "de", "PA": "do", "PB": "da",
    "PR": "do", "PE": "de", "PI": "do", "RJ": "do", "RN": "do", "RS": "do", "RO": "de",
    "RR": "de", "SC": "de", "SP": "de", "SE": "de", "TO": "do",
}
# Os 33 Tribunais de Contas do Brasil: sigla -> (UF, nome). Deve coincidir com a aba "Listas".
TRIBUNAIS = {
    "TCU": ("DF", "Tribunal de Contas da União"),
    "TCDF": ("DF", "Tribunal de Contas do Distrito Federal"),
    **{f"TCE-{uf}": (uf, f"Tribunal de Contas do Estado {p} {UF_NOME[uf]}") for uf, p in _PREP.items()},
    "TCM-BA": ("BA", "Tribunal de Contas dos Municípios do Estado da Bahia"),
    "TCM-GO": ("GO", "Tribunal de Contas dos Municípios do Estado de Goiás"),
    "TCM-PA": ("PA", "Tribunal de Contas dos Municípios do Estado do Pará"),
    "TCM-RJ": ("RJ", "Tribunal de Contas do Município do Rio de Janeiro"),
    "TCM-SP": ("SP", "Tribunal de Contas do Município de São Paulo"),
}
TIPOS = {"Conformidade", "Financeira", "Operacional"}
TURMA = re.compile(r"^(Inglês|Espanhol|Francês|Árabe|Português) (20\d\d)$")
COLUNAS = ["Nome", "Tribunal", "Turma", "Tipo de auditoria"]


def normal(s):
    s = unicodedata.normalize("NFD", " ".join(str(s).split()).lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def ler_csv(origem):
    if re.match(r"^https?://", origem):
        with urllib.request.urlopen(origem, timeout=60) as r:
            texto = r.read().decode("utf-8-sig")
    else:
        texto = Path(origem).read_text(encoding="utf-8-sig")
    return list(csv.reader(io.StringIO(texto)))


def validar(linhas):
    """Devolve (auditores, erros). Qualquer erro impede a publicação."""
    erros = []
    if not linhas or [c.strip() for c in linhas[0][:4]] != COLUNAS:
        return [], [f"Cabeçalho inesperado: {linhas[0] if linhas else '(vazio)'}; esperado {COLUNAS}. "
                    "Confira se a URL publicada é a da aba Publicação."]
    auditores, vistos = [], {}
    for n, lin in enumerate(linhas[1:], start=2):
        lin = [c.strip() for c in lin] + [""] * 4
        nome, trib, turma, tipo = (" ".join(lin[0].split()), lin[1], lin[2], lin[3])
        if not any((nome, trib, turma, tipo)):
            continue
        if not nome:
            erros.append(f"Linha {n}: nome vazio.")
        if trib not in TRIBUNAIS:
            erros.append(f"Linha {n} ({nome}): tribunal desconhecido {trib!r}.")
        if not TURMA.match(turma):
            erros.append(f"Linha {n} ({nome}): turma inválida {turma!r} (ex.: 'Inglês 2025').")
        if tipo not in TIPOS:
            erros.append(f"Linha {n} ({nome}): tipo de auditoria inválido {tipo!r}.")
        chave = (normal(nome), trib, tipo)
        if chave in vistos:
            erros.append(f"Linha {n} ({nome}): repetida (mesmo nome, tribunal e tipo da linha {vistos[chave]}).")
        vistos[chave] = n
        auditores.append({"nome": nome, "tribunal": trib, "turma": turma, "tipo": tipo})
    auditores.sort(key=lambda a: normal(a["nome"]))
    return auditores, erros


def ordem_turma(t):
    lingua, ano = TURMA.match(t).groups()
    return (ano, lingua)


# ---------- mapa ----------
LAT0 = math.cos(math.radians(-15))
LON_MIN, LON_MAX, LAT_MIN, LAT_MAX = -74.2, -28.6, -33.9, 5.4
LARG = 600


def proj(lon, lat):
    esc = LARG / ((LON_MAX - LON_MIN) * LAT0)
    return ((lon - LON_MIN) * LAT0 * esc, (LAT_MAX - lat) * esc)


def dp(pts, tol):
    """Douglas-Peucker: remove vértices que desviam menos que `tol` da reta."""
    if len(pts) < 3:
        return pts
    (x1, y1), (x2, y2) = pts[0], pts[-1]
    dx, dy = x2 - x1, y2 - y1
    norma = math.hypot(dx, dy) or 1e-9
    idx, dmax = 0, 0.0
    for i in range(1, len(pts) - 1):
        d = abs(dy * pts[i][0] - dx * pts[i][1] + x2 * y1 - y2 * x1) / norma
        if d > dmax:
            idx, dmax = i, d
    if dmax <= tol:
        return [pts[0], pts[-1]]
    return dp(pts[: idx + 1], tol)[:-1] + dp(pts[idx:], tol)


def mapa(geojson):
    d = json.load(open(geojson, encoding="utf-8"))
    estados = {}
    for f in d["features"]:
        uf = f["properties"]["sigla"]
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        partes, cx, cy, area_tot = [], 0.0, 0.0, 0.0
        for poly in polys:
            anel = [proj(x, y) for x, y in poly[0]]
            # anel fechado: divide no vértice mais distante do início, senão a "reta" do DP tem comprimento zero
            k = max(range(len(anel)), key=lambda i: math.dist(anel[0], anel[i]))
            s = dp(anel[: k + 1], 0.35)[:-1] + dp(anel[k:], 0.35)
            if len(s) < 4:
                continue
            partes.append("M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in s) + "Z")
            # centróide do maior polígono (para rótulo)
            a = sum(anel[i][0] * anel[i - 1][1] - anel[i - 1][0] * anel[i][1] for i in range(len(anel))) / 2
            if abs(a) > area_tot:
                area_tot = abs(a)
                cx = sum((anel[i][0] + anel[i - 1][0]) * (anel[i][0] * anel[i - 1][1] - anel[i - 1][0] * anel[i][1]) for i in range(len(anel))) / (6 * a)
                cy = sum((anel[i][1] + anel[i - 1][1]) * (anel[i][0] * anel[i - 1][1] - anel[i - 1][0] * anel[i][1]) for i in range(len(anel))) / (6 * a)
        estados[uf] = {"nome": UF_NOME[uf], "d": "".join(partes), "x": round(cx, 1), "y": round(cy, 1)}
    _, alt = proj(LON_MIN, LAT_MIN)
    return {"largura": LARG, "altura": round(alt), "estados": estados}



if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Gera dados.js do Cadastro a partir da aba Publicação.")
    ap.add_argument("--csv", required=True, help="URL publicada (CSV) da aba Publicação, ou caminho de um CSV local")
    ap.add_argument("--mapa", type=Path, metavar="GEOJSON", help="regera mapa.js (raramente necessário)")
    args = ap.parse_args()
    raiz = Path(__file__).resolve().parent.parent

    auditores, erros = validar(ler_csv(args.csv))
    if erros:
        print("Dados NÃO publicados. Corrija na aba Controle da planilha:", *erros, sep="\n  ", file=sys.stderr)
        sys.exit(1)

    destino = raiz / "dados.js"
    hoje = datetime.date.today().isoformat()
    atualizado = hoje
    if destino.exists():  # mantém a data anterior se a lista não mudou (evita commits diários vazios)
        txt = destino.read_text(encoding="utf-8")
        anterior = json.loads(txt[txt.index("{"):txt.rindex("}") + 1])
        if anterior.get("auditores") == auditores:
            atualizado = anterior.get("atualizado", hoje)

    turmas = sorted({a["turma"] for a in auditores}, key=ordem_turma)
    dados = {
        "atualizado": atualizado,
        "turmas": {t: t for t in turmas},
        "tribunais": [{"sigla": s, "uf": uf, "nome": nome} for s, (uf, nome) in sorted(TRIBUNAIS.items())],
        "auditores": auditores,
    }
    destino.write_text(
        "/* Cadastro Nacional de Auditores de Controle Externo Certificados: auditores com certificação vigente.\n"
        "   Gerado por ferramentas/gerar_dados.py a partir da planilha de controle. Não editar à mão. */\n"
        "window.CADASTRO = " + json.dumps(dados, ensure_ascii=False, indent=1) + ";\n", encoding="utf-8")
    print(f"{len(auditores)} auditores com certificação vigente; atualizado em {atualizado}")

    if args.mapa:
        (raiz / "mapa.js").write_text(
            "/* Contornos simplificados das UFs (fonte: IBGE via codeforamerica/click_that_hood). */\n"
            "window.MAPA_BR = " + json.dumps(mapa(args.mapa), ensure_ascii=False) + ";\n", encoding="utf-8")
        print("mapa.js regerado")
