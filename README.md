# Cadastro Nacional de Auditores de Controle Externo Certificados

Página pública do Cadastro mantido pela ANTC, nos termos do Acordo de Cooperação Técnica
TCU–IRB–ANTC (cláusula quinta), com os auditores dos Tribunais de Contas brasileiros
com certificação **PESA** (Professional Education for SAI Auditors), da IDI/INTOSAI, **vigente**.

Endereço: **https://cadastro.antcbrasil.org.br/** (o antigo https://antc-brasil.github.io/cadastro/ redireciona para ele).

- **Página:** `index.html` (layout, mapa e filtros) + `dados.js` (auditores) + `mapa.js` (contornos das UFs).
  Arquivos estáticos, sem servidor.
- **Dados:** planilha Google de controle da ANTC (fora deste repositório). Só são publicados
  nome, Tribunal de Contas, turma e tipo de auditoria dos auditores com situação **Vigente**.
- **Hospedagem:** GitHub Pages. O workflow `.github/workflows/publicar.yml` lê a planilha todo dia
  às 6h (Brasília), a cada push na `main` e quando acionado à mão (*Actions → Publicar cadastro → Run workflow*).

## Planilha de controle

A planilha pertence à conta Google institucional da ANTC (Workspace `antcbrasil.org.br`).

| Aba | Conteúdo | Publicada? |
|---|---|---|
| **Controle** | Todos os auditores: nome, tribunal, turma, tipo, **situação** (Em formação, Vigente, Expirada), ano de certificação, última verificação e observações | Não |
| **Publicação** | Fórmula `QUERY` sobre a Controle: só as 4 colunas públicas e só as linhas **Vigente**. Não editar | Sim, como CSV |
| **Listas** | Siglas dos 33 Tribunais de Contas, turmas, tipos e situações que alimentam as listas suspensas | Não |

Para incluir, certificar ou retirar um auditor, edite **apenas a aba Controle**. A página reflete a mudança
na próxima execução do workflow (no máximo em 24 horas, ou na hora, com *Run workflow*).

Nova turma: acrescente na aba **Listas** (coluna Turma) no formato `Idioma AAAA`, por exemplo `Inglês 2027`.

## O que o workflow faz

1. baixa a aba **Publicação** (variável `PLANILHA_CSV`, em *Settings → Secrets and variables → Actions → Variables*);
2. valida cada linha: tribunal entre os 33 conhecidos, turma no formato `Idioma AAAA`, tipo de auditoria válido,
   sem linhas repetidas;
3. **se houver qualquer erro, para sem publicar** (a versão no ar continua a anterior) e mostra o motivo no log;
4. se a lista mudou, grava o novo `dados.js` no repositório (commit automático, que serve de histórico);
5. publica a página.

Para testar localmente:

```bash
python3 ferramentas/gerar_dados.py --csv "URL-ou-caminho-do-CSV"
python3 -m http.server 8000
```

> Atenção: num repositório público, o histórico do git guarda todas as versões de `dados.js`.
> Confira a aba Controle antes de marcar alguém como Vigente.

## Implantação (uma única vez)

1. **GitHub:** repositório público `antc-brasil/cadastro` (feito).
2. **Pages:** em *Settings → Pages*, origem **GitHub Actions** (feito).
3. **Planilha:** na planilha de controle, *Arquivo → Compartilhar → Publicar na Web*, escolher a aba **Publicação**
   e o formato **CSV**. Copiar a URL gerada para a variável `PLANILHA_CSV` do repositório.
4. **Verificar o domínio** na organização (*Settings → Pages → Add a domain*). Se for verificado
   `antcbrasil.org.br` inteiro, os subdomínios futuros não precisarão de nova verificação. O GitHub informa o TXT.
5. **DNS de antcbrasil.org.br** (pedido à Trídia):

   | Tipo  | Nome                                 | Valor                         |
   |-------|--------------------------------------|-------------------------------|
   | CNAME | `cadastro`                           | `antc-brasil.github.io.`      |
   | TXT   | *(o que o GitHub indicar no passo 4)* | *(valor informado pelo GitHub)* |

   Com os registros no ar: **Verify** na organização → *Custom domain* no repositório → **Enforce HTTPS**.

   Situação em 18/11/2026: CNAME criado pela Trídia, *Custom domain* e HTTPS ativos. A verificação do domínio
   na organização (registro TXT) ainda não foi feita; ela protege o subdomínio contra uso por outro repositório.
6. **Site da ANTC:** botão ou banner "Cadastro Nacional de Auditores Certificados" com link para a página (pendente).
