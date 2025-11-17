# Simulador Jurídico para Estudantes

Aplicativo simples em Streamlit para treinar argumentação jurídica a partir de casos e princípios mapeados em CSV.

---

## 📁 Estrutura do Projeto

```
simulador_juridico_estudantes/
├── app.py                 # Aplicação principal
├── utils.py               # Funções de processamento
├── data/
│   └── principios.csv     # Base de casos e princípios
├── requirements.txt       # Dependências
└── README.md             # Este arquivo
```

---

## ⚙️ Pré-requisitos

- Python **3.10 ou superior** recomendado

---

## 🚀 Como Rodar (Local)

### 1. Criar e ativar ambiente virtual

```bash
python -m venv venv

# Linux/Mac
source venv/bin/activate

# Windows (PowerShell)
venv\Scripts\Activate.ps1
```

### 2. Instalar dependências

```bash
pip install -r requirements.txt
```

### 3. Executar aplicação

```bash
streamlit run app.py
# ou
python -m streamlit run app.py
```

### 4. Acessar no navegador

Abra: **http://localhost:8501**

---

## 📋 Como Usar

Na interface:

1. **Selecione a fonte de dados** na barra lateral (`data/principios.csv` ou um CSV próprio)
2. **Selecione o caso** desejado
3. **Escolha o lado** (acusacao ou defesa)
4. **Digite seus argumentos** no campo de texto
5. **Clique em "Avaliar argumentação"**

---

## 📊 Esquema do CSV (Colunas Obrigatórias)

| Coluna | Descrição | Exemplo |
|--------|------------|---------|
| `case_id` | ID único do caso | `1` |
| `case_title` | Título do caso | `"Cotas Raciais nas Universidades"` |
| `case_description` | Descrição do caso | `"STF analisou constitucionalidade..."` |
| `side` | `"acusacao"` ou `"defesa"` | `"defesa"` |
| `principle` | Princípio jurídico | `"Igualdade material"` |
| `article` | Artigo/legislação | `"Art. 5º, caput, CF/88"` |
| `weight` | Peso (decimal) | `1.0` |
| `keywords` | Termos separados por `;` ou `,` | `"igualdade;inclusão;minorias"` |

**Observações:**
- Campos com vírgulas devem estar entre aspas: `"Art. 5º, XXII, CF/88"`
- `weight` é usado no cálculo da pontuação

### Exemplo de CSV

```csv
case_id,case_title,case_description,side,principle,article,weight,keywords
1,Furto de celular,"Subtração de celular em via pública",acusacao,Direito de propriedade,"Art. 5º, XXII, CF/88",1.0,"direito de propriedade;propriedade;furto"
1,Furto de celular,"Subtração de celular em via pública",defesa,Princípio da proporcionalidade,"Doutrina e jurisprudência",1.0,"proporcionalidade;pena;culpa"
```

---

## 🎯 Sistema de Pontuação

- **Pontuação máxima** = Soma de todos os `weight` para o caso/lado selecionado
- **Pontuação obtida** = Soma dos `weight` dos princípios identificados no texto
- **Formato de exibição**: `Pontuação obtida: 3,0/10,0 pontos`

**Exemplo:**
- Caso tem 4 princípios com pesos: 1.0, 2.0, 1.5, 0.5 → **Máximo = 5,0**
- Usuário identifica 2 princípios (1.0 + 1.5) → **Obtido = 2,5**
- **Resultado**: `Pontuação obtida: 2,5/5,0 pontos`

---

## 📦 Dependências

### `requirements.txt`

```txt
streamlit>=1.29
pandas>=2.0
```

---

## 💡 Dicas de Uso

- Se o comando `streamlit` não for reconhecido, confirme se o ambiente virtual está ativo
- Para melhor pontuação, use palavras-chave diretas como:
  - `"CF 5º"`, `"dignidade"`, `"igualdade material"`
  - `"função social"`, `"direito à saúde"`
- Verifique se:
  - O `side` no CSV coincide exatamente com o lado escolhido
  - O campo `keywords` está preenchido
  - Campos com vírgulas estão entre aspas

---

## 🔧 Solução de Problemas

**Sem pontuação?**
- Verifique se há keywords cadastradas para o caso/lado
- Confirme a formatação do CSV
- Use palavras-chave mais objetivas no texto

**Erro ao carregar CSV?**
- Verifique as colunas obrigatórias
- Confirme a formatação de campos com vírgula