"""Gera dados.js (auditores) e mapa.js (contornos dos estados) para a página do Cadastro.

Uso:
  python3 ferramentas/gerar_dados.py <planilha.xlsx> [--atualizado AAAA-MM] [--mapa brazil-states.geojson]

Requer: pip install openpyxl

Fonte dos auditores: aba "MAPA - GRÁFICO" (tribunal, tipo, nome, turma),
complementada pelo e-mail da aba "ANALÍTICO" (usado só internamente, para identificar
o tribunal das indicações feitas pelo IRB; o e-mail NÃO é gravado em dados.js) (mesma ordem de linhas; o script
confere nome + tribunal linha a linha e aborta se divergirem).
"""
import json
import math
import sys

import openpyxl

# Código bruto da planilha -> (sigla de exibição, UF, nome por extenso)
TRIBUNAIS = {
    "TCU": ("TCU", "DF", "Tribunal de Contas da União"),
    "TCU/ONU": ("TCU", "DF", "Tribunal de Contas da União"),
    "TCDF": ("TCDF", "DF", "Tribunal de Contas do Distrito Federal"),
    "TCMBA": ("TCM-BA", "BA", "Tribunal de Contas dos Municípios do Estado da Bahia"),
    "TCMGO": ("TCM-GO", "GO", "Tribunal de Contas dos Municípios do Estado de Goiás"),
    "TCMSP": ("TCM-SP", "SP", "Tribunal de Contas do Município de São Paulo"),
    "TCMRJ": ("TCM-RJ", "RJ", "Tribunal de Contas do Município do Rio de Janeiro"),
}
UF_NOME = {
    "AC": "Acre", "AL": "Alagoas", "AP": "Amapá", "AM": "Amazonas", "BA": "Bahia",
    "CE": "Ceará", "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás",
    "MA": "Maranhão", "MT": "Mato Grosso", "MS": "Mato Grosso do Sul", "MG": "Minas Gerais",
    "PA": "Pará", "PB": "Paraíba", "PR": "Paraná", "PE": "Pernambuco", "PI": "Piauí",
    "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte", "RS": "Rio Grande do Sul",
    "RO": "Rondônia", "RR": "Roraima", "SC": "Santa Catarina", "SP": "São Paulo",
    "SE": "Sergipe", "TO": "Tocantins",
}
# Preposição correta no nome do TCE ("do Estado de/do/da ...")
UF_PREP = {
    "AC": "do", "AL": "de", "AP": "do", "AM": "do", "BA": "da", "CE": "do", "ES": "do",
    "GO": "de", "MA": "do", "MT": "de", "MS": "de", "MG": "de", "PA": "do", "PB": "da",
    "PR": "do", "PE": "de", "PI": "do", "RJ": "do", "RN": "do", "RS": "do", "RO": "de",
    "RR": "de", "SC": "de", "SP": "de", "SE": "de", "TO": "do",
}
# Indicações feitas pelo IRB: o tribunal de origem é deduzido do domínio do e-mail
DOMINIO = {"tce.pr.gov.br": "TCEPR", "tcmsp.tc.br": "TCMSP"}

TIPOS = {"AOP": "Operacional", "CONFORMIDADE": "Conformidade", "FINANCEIRA": "Financeira"}
TURMAS = {
    "INGL25": ("ING25", "Inglês 2025"),
    "ESP25": ("ESP25", "Espanhol 2025"),
    "ING26": ("ING26", "Inglês 2026"),
    "ESP26": ("ESP26", "Espanhol 2026"),
}


def tribunal(codigo, email):
    if codigo.startswith("IRB"):
        codigo = DOMINIO.get((email or "").split("@")[-1].lower(), codigo)
    if codigo in TRIBUNAIS:
        return TRIBUNAIS[codigo]
    if codigo.startswith("TCE") and len(codigo) == 5:
        uf = codigo[3:]
        return (f"TCE-{uf}", uf, f"Tribunal de Contas do Estado {UF_PREP[uf]} {UF_NOME[uf]}")
    raise ValueError(f"Tribunal não mapeado: {codigo}")


def auditores(xlsx):
    wb = openpyxl.load_workbook(xlsx, data_only=True)
    mapa = list(wb["MAPA - GRÁFICO"].iter_rows(min_row=2, values_only=True))
    anal = list(wb["ANALÍTICO"].iter_rows(min_row=2, values_only=True))
    saida, tribs, vistos, pend = [], {}, set(), []
    for m, a in zip(mapa, anal):
        if not m[7]:
            continue
        if (m[7], m[5]) != (a[7], a[5]):
            raise SystemExit(f"Linhas desalinhadas no ID {m[0]}: {m[7]!r} x {a[7]!r}")
        emails = (a[8] or "").strip().lower().split()
        email = emails[0] if emails else None
        if not m[6]:
            pend.append((m[0], m[7], "tipo de auditoria não informado", ""))
        sigla, uf, nome_trib = tribunal(m[5], email)
        chave = (normal(m[7]), sigla, m[8], m[6])
        if chave in vistos:
            pend.append((m[0], m[7], "linha duplicada (mesmo nome, tribunal, turma e tipo) — omitida", ""))
            continue
        vistos.add(chave)
        tribs[sigla] = {"sigla": sigla, "uf": uf, "nome": nome_trib}
        turma = TURMAS[m[8]]
        saida.append({
            "nome": " ".join(str(m[7]).split()),
            "_email": email,  # só para o relatório de pendências; removido antes de gravar
            "tribunal": sigla,
            "turma": turma[0],
            "tipo": TIPOS.get(m[6]),  # None = não informado na planilha
            "_id": m[0],
        })
    # mesmo nome em mais de uma linha restante: pode ser legítimo (duas turmas) ou erro (tribunal/e-mail trocado)
    por_nome = {}
    for r in saida:
        por_nome.setdefault(normal(r["nome"]), []).append(r)
    for rs in por_nome.values():
        if len(rs) > 1:
            desc = " ; ".join(f'{r["tribunal"]}/{r["turma"]}/{r["tipo"]}/{r["_email"]}' for r in rs)
            for r in rs:
                pend.append((r["_id"], r["nome"], "nome repetido em outra linha — conferir", desc))
    for r in saida:
        del r["_id"], r["_email"]
    return saida, sorted(tribs.values(), key=lambda t: t["sigla"]), {k: v for k, v in TURMAS.values()}, pend


def normal(s):
    import unicodedata
    s = unicodedata.normalize("NFD", " ".join(str(s).split()).lower())
    return "".join(c for c in s if not unicodedata.combining(c))


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
    import argparse
    import csv
    import datetime
    from pathlib import Path

    ap = argparse.ArgumentParser(description="Gera dados.js (e, opcionalmente, mapa.js) do Cadastro.")
    ap.add_argument("planilha", type=Path, help="planilha .xlsx com as abas MAPA - GRÁFICO e ANALÍTICO")
    ap.add_argument("--atualizado", default=datetime.date.today().strftime("%Y-%m"),
                    help="mês de referência dos dados, AAAA-MM (padrão: mês atual)")
    ap.add_argument("--mapa", type=Path, metavar="GEOJSON",
                    help="regera mapa.js a partir de um GeoJSON de UFs (raramente necessário)")
    args = ap.parse_args()

    raiz = Path(__file__).resolve().parent.parent  # raiz do repositório
    lista, tribs, turmas, pend = auditores(args.planilha)

    # O relatório de pendências contém dados para conferência: fica ao lado da planilha, FORA do repositório
    rel = args.planilha.resolve().parent / "pendencias_validacao.csv"
    with open(rel, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["ID planilha", "Nome", "Pendência", "Detalhe"])
        w.writerows(sorted(pend, key=lambda p: (p[2], p[0])))
    print(len(pend), "pendências em", rel)

    with open(raiz / "dados.js", "w", encoding="utf-8") as f:
        f.write("/* Cadastro Nacional de Auditores de Controle Externo Certificados — dados gerados por gerar_dados.py.\n"
                "   DADOS PRELIMINARES, EM VALIDAÇÃO. Não editar à mão: regenerar a partir da planilha. */\n")
        f.write("window.CADASTRO = " + json.dumps(
            {"atualizado": args.atualizado, "turmas": turmas, "tribunais": tribs, "auditores": lista},
            ensure_ascii=False, indent=1) + ";\n")
    print(len(lista), "auditores;", len(tribs), "tribunais →", raiz / "dados.js")

    if args.mapa:
        with open(raiz / "mapa.js", "w", encoding="utf-8") as f:
            f.write("/* Contornos simplificados das UFs (fonte: IBGE via codeforamerica/click_that_hood). */\n")
            f.write("window.MAPA_BR = " + json.dumps(mapa(args.mapa), ensure_ascii=False) + ";\n")
        print("mapa.js regerado")
