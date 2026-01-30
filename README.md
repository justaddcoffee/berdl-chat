# BERDL Chat

Natural language chat interface to the [BERDL Data Lakehouse](https://hub.berdl.kbase.us) (NMDC microbiome data).

Ask questions in plain English, get SQL queries executed against BERDL, and receive explanations of the results.

## Features

- Natural language to SQL conversion via Claude
- Live execution against BERDL lakehouse
- Plain English result explanations
- Collapsible SQL view
- Example question buttons
- Connection status indicator

## Setup

1. Clone the repo:
   ```bash
   git clone https://github.com/justaddcoffee/berdl-chat.git
   cd berdl-chat
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

3. Create `.env` file with your credentials:
   ```bash
   cp .env.example .env
   # Edit .env with your tokens
   ```

   You'll need:
   - `KB_AUTH_TOKEN` - Get from BERDL JupyterHub:
     ```python
     import os
     print(os.environ.get('KBASE_AUTH_TOKEN'))
     ```
   - `ANTHROPIC_API_KEY` - Get from [Anthropic Console](https://console.anthropic.com/)

4. Run the app:
   ```bash
   uv run python main.py
   ```

5. Open http://localhost:8081 in your browser

## Example Questions

- "How many samples have plastic degradation?"
- "What kingdoms are in the taxonomy?"
- "Show samples with methanogenesis"
- "Count studies by ecosystem type"

## Available Data

The app queries the `nmdc_core` database which includes:

- **trait_features** - 90+ predicted microbial functional traits per sample
- **abiotic_features** - Environmental measurements (pH, temp, depth, etc.)
- **taxonomy_dim** - 2.6M taxonomy records
- **study_table** - 48 NMDC studies
- **cog_categories** - COG functional categories

## License

MIT
