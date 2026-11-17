# Cadastro Nacional de Auditores de Controle Externo Certificados

Página pública do Cadastro mantido pela ANTC, nos termos do Acordo de Cooperação Técnica
TCU–IRB–ANTC (cláusula quinta), com os auditores dos Tribunais de Contas brasileiros
que participam da certificação **PESA** (Professional Education for SAI Auditors), da IDI/INTOSAI.

Endereço previsto: **https://cadastro.antcbrasil.org.br/** (ajustar se for escolhido outro subdomínio).

- **Página:** `index.html` (layout, mapa e filtros) + `dados.js` (auditores) + `mapa.js` (contornos das UFs).
  Arquivos estáticos, sem servidor.
- **Dados:** gerados **localmente** por `ferramentas/gerar_dados.py` a partir da planilha do IRB.
  A planilha **não** fica no repositório (contém telefone, gênero e dados dos coaches; ver `.gitignore`).
  Só os campos divulgados vão para `dados.js`: nome, Tribunal de Contas, turma e tipo de auditoria.
  O e-mail é lido apenas para identificar o tribunal das indicações feitas pelo IRB e **não** é publicado.
- **Hospedagem:** GitHub Pages. O workflow `.github/workflows/publicar.yml` publica a cada push na `main`.

## Atualizar os dados

```bash
pip install openpyxl
python3 ferramentas/gerar_dados.py "/caminho/da/planilha.xlsx" --atualizado 2026-10
```

O script:

1. lê a aba **MAPA - GRÁFICO** e confere, pela aba **ANALÍTICO**, o e-mail (uso interno) (aborta se as linhas não baterem);
2. omite linhas duplicadas exatas (mesmo nome, tribunal, turma e tipo);
3. grava `dados.js` na raiz deste repositório;
4. grava `pendencias_validacao.csv` **ao lado da planilha** (fora do repositório) para conferência.

Depois, revise a página localmente (`python3 -m http.server` nesta pasta e abra http://localhost:8000),
faça commit **apenas** de `dados.js` e envie. A publicação leva cerca de 1 minuto.

> Atenção: num repositório público, o histórico do git guarda todas as versões enviadas.
> Confira os dados **antes** do envio; apagar um dado depois não o remove do histórico.

Novos tribunais ou turmas: incluir em `TRIBUNAIS`/`TURMAS` no início de `gerar_dados.py`
(o script aborta e avisa quando encontra um código desconhecido).

## Implantação (uma única vez)

1. **GitHub:** na organização `antc-brasil`, criar o repositório público `cadastro` com o conteúdo desta pasta.
2. **Pages:** em *Settings → Pages* do repositório, origem **GitHub Actions**. O primeiro push publica em
   https://antc-brasil.github.io/cadastro/ (endereço provisório, bom para conferir).
3. **Verificar o domínio** na organização (*Settings → Pages → Add a domain*). Se for verificado
   `antcbrasil.org.br` inteiro, os subdomínios futuros não precisarão de nova verificação. O GitHub informa o TXT.
4. **DNS de antcbrasil.org.br** (pedido à Trídia):

   | Tipo  | Nome                                 | Valor                         |
   |-------|--------------------------------------|-------------------------------|
   | CNAME | `cadastro`                           | `antc-brasil.github.io.`      |
   | TXT   | *(o que o GitHub indicar no passo 3)* | *(valor informado pelo GitHub)* |

   Com os registros no ar: **Verify** na organização → *Custom domain* no repositório → **Enforce HTTPS**.
5. **Site da ANTC:** botão ou banner "Cadastro Nacional de Auditores Certificados" com link para a página.

## Antes da primeira publicação

- [ ] Planilha validada com o IRB/TCU (ver `pendencias_validacao.csv`).
- [x] Padronização da grafia dos nomes (`formatarNome` em `index.html`).
