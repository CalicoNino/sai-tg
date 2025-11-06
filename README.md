# SAI Telegram Bot

A simple Telegram bot to query the SAI GraphQL endpoint and display trades and oracle prices based on user inputs.

- GraphQL endpoint: `https://sai-keeper.testnet-2.nibiru.fi/query`

## Features

- ✅ Query trades for any wallet address directly
- ✅ View open or closed trades with pagination
- ✅ Filter trades by asset symbol (e.g., `/trades <address> btc`)
- ✅ Display oracle prices for all tokens with pagination (top 10 by default)
- ✅ Get price for a specific token (e.g., `/price btc`)
- ✅ No database required - just direct GraphQL queries
- ✅ Works in both private chats and group chats

## Setup

1. Create a bot via [BotFather](https://t.me/botfather) and get your bot token

2. Copy the example environment file and add your token:

```bash
cp env.example .env
```

3. Edit `.env` and add your bot token:

```ini
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

The `SAI_GRAPHQL_ENDPOINT` is optional (defaults to testnet endpoint). Uncomment and modify if needed.

4. Install dependencies (Python 3.10+ recommended):

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run

```bash
python -m bot.main
```

## Commands

- `/start` or `/help` – Show help message
- `/trades <wallet_address> [open|closed] [btc]` – View trades for a wallet
  - Supports both Nibiru (`nibiru1...`) and Ethereum (`0x...`) addresses
  - Example: `/trades nibiru1abc123...`
  - Example: `/trades 0x1234abcd...`
  - Example: `/trades nibiru1abc123... open` (only open trades)
  - Example: `/trades 0x1234abcd... closed` (only closed trades)
  - Example: `/trades nibiru1abc123... btc` (only BTC trades)
  - Example: `/trades 0x1234abcd... open btc` (only open BTC trades)
- `/prices [next]` – Show oracle prices (top 10 by default, use `next` for more)
- `/price <symbol>` – Get price for a specific token (e.g., `/price btc`)

## Examples

```
# Nibiru addresses
/trades nibiru1abc123def456...
/trades nibiru1abc123def456... open
/trades nibiru1abc123def456... closed
/trades nibiru1abc123def456... btc
/trades nibiru1abc123def456... open btc

# Ethereum addresses
/trades 0x1234abcd5678ef90...
/trades 0x1234abcd5678ef90... open
/trades 0x1234abcd5678ef90... closed
/trades 0x1234abcd5678ef90... btc

# Price commands
/prices
/prices next
/price btc
/price eth
```

## Trade Information

### Open Trades
- Position value (in macro units)
- PnL (Profit/Loss) and PnL percentage
- Liquidation price
- Entry price
- Collateral amount

### Closed Trades
- Entry and exit prices
- Collateral amount
- Open and close timestamps

## Price Display

- Popular tokens (BTC, ETH, USDT, etc.) are shown first
- Prices are formatted based on value:
  - Large prices: 2 decimal places (e.g., `$50,000.00`)
  - Medium prices: 4 decimal places (e.g., `$0.1234`)
  - Small prices: 8 decimal places (e.g., `$0.00001234`)
- Pagination with "Next →" button for browsing more prices

## Notes

- Data source: SAI keeper GraphQL endpoint
- No database storage - all queries are direct to GraphQL API
- Trades are formatted with clear visual separators and emojis for easy reading
- Monetary values in trades are displayed in macro units (divided by 10^6)
- The bot works in both private chats and group chats

## Project Structure

```
sai-tg/
├── bot/
│   ├── __init__.py          # Package marker
│   ├── main.py              # Main bot application
│   └── graphql.py           # GraphQL client
├── .env                     # Environment variables (create this)
├── env.example              # Example environment file
├── requirements.txt         # Python dependencies
├── README.md                # This file
└── BUILD_GUIDE.md          # Detailed build guide
```

## License

MIT
