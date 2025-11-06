import os
import logging
from typing import Optional, Dict

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from .graphql import SaiGQLClient


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def format_trade_open(trade: dict) -> str:
    """Format an open trade for display."""
    trade_id = trade.get('id', '?')
    is_long = trade.get('isLong', False)
    side = "🟢 Long" if is_long else "🔴 Short"
    
    mkt = trade.get("perpBorrowing", {})
    base_token = mkt.get("baseToken") or {}
    quote_token = mkt.get("quoteToken") or {}
    base = base_token.get("symbol") or base_token.get("name") or "?"
    quote = quote_token.get("symbol") or quote_token.get("name") or "?"
    market_id = mkt.get("marketId", "?")
    
    leverage = trade.get('leverage')
    open_price = trade.get('openPrice')
    collateral = trade.get('collateralAmount')
    open_collateral = trade.get('openCollateralAmount')
    
    state = trade.get('state') or {}
    position_value = state.get('positionValue')
    liquidation_price = state.get('liquidationPrice')
    pnl = state.get('pnlCollateral')
    pnl_pct = state.get('pnlPct')
    
    open_block = trade.get("openBlock") or {}
    open_ts = open_block.get("block_ts")
    
    lines = [
        f"━━━━━━━━━━━━━━━━━━━━",
        f"Trade #{trade_id} | ✅ OPEN",
        f"Market: {base}/{quote} (ID: {market_id})",
        f"Side: {side} | Leverage: {leverage}x",
        f"Entry Price: {open_price}",
    ]
    
    if liquidation_price:
        lines.append(f"Liquidation Price: {liquidation_price}")
    
    if position_value is not None:
        position_value_macro = position_value / (10 ** 6)
        lines.append(f"Position Value: ${position_value_macro:,.2f}")
    
    if pnl is not None:
        pnl_macro = pnl / (10 ** 6)
        pnl_sign = "+" if pnl_macro >= 0 else ""
        lines.append(f"PnL: {pnl_sign}${pnl_macro:,.2f}")
    
    if pnl_pct is not None:
        pnl_sign = "+" if pnl_pct >= 0 else ""
        lines.append(f"PnL %: {pnl_sign}{pnl_pct:.2f}%")
    
    if open_collateral:
        open_collateral_macro = open_collateral / (10 ** 6)
        lines.append(f"Collateral: {open_collateral_macro:,.2f}")
    if collateral and collateral != open_collateral:
        collateral_macro = collateral / (10 ** 6)
        lines.append(f"Current Collateral: {collateral_macro:,.2f}")
    
    if open_ts:
        lines.append(f"Opened: {open_ts}")
    
    return "\n".join(lines)


def format_trade_closed(trade: dict) -> str:
    """Format a closed trade for display."""
    trade_id = trade.get('id', '?')
    is_long = trade.get('isLong', False)
    side = "🟢 Long" if is_long else "🔴 Short"
    
    mkt = trade.get("perpBorrowing", {})
    base_token = mkt.get("baseToken") or {}
    quote_token = mkt.get("quoteToken") or {}
    base = base_token.get("symbol") or base_token.get("name") or "?"
    quote = quote_token.get("symbol") or quote_token.get("name") or "?"
    market_id = mkt.get("marketId", "?")
    
    leverage = trade.get('leverage')
    open_price = trade.get('openPrice')
    close_price = trade.get('closePrice')
    open_collateral = trade.get('openCollateralAmount')
    
    open_block = trade.get("openBlock") or {}
    close_block = trade.get("closeBlock") or {}
    open_ts = open_block.get("block_ts")
    close_ts = close_block.get("block_ts")
    
    lines = [
        f"━━━━━━━━━━━━━━━━━━━━",
        f"Trade #{trade_id} | ❌ CLOSED",
        f"Market: {base}/{quote} (ID: {market_id})",
        f"Side: {side} | Leverage: {leverage}x",
        f"Entry Price: {open_price}",
    ]
    
    if close_price:
        lines.append(f"Exit Price: {close_price}")
    
    if open_collateral:
        open_collateral_macro = open_collateral / (10 ** 6)
        lines.append(f"Collateral: {open_collateral_macro:,.2f}")
    
    if open_ts:
        lines.append(f"Opened: {open_ts}")
    if close_ts:
        lines.append(f"Closed: {close_ts}")
    
    return "\n".join(lines)


# Popular tokens to show first
POPULAR_TOKENS = ["BTC", "ETH", "USDT", "USDC", "NIBI", "ATOM", "SOL", "BNB", "AVAX", "MATIC"]

def format_prices(prices: list, start_idx: int = 0, page_size: int = 10) -> tuple[str, bool]:
    """Format token prices for display. Returns (formatted_text, has_more)."""
    if not prices:
        return "No prices found.", False
    
    # Sort: popular tokens first, then by token_id
    def sort_key(p):
        token = p.get("token") or {}
        symbol = (token.get("symbol") or "").upper()
        if symbol in POPULAR_TOKENS:
            return (0, POPULAR_TOKENS.index(symbol))
        return (1, token.get("id", 9999))
    
    sorted_prices = sorted(prices, key=sort_key)
    
    end_idx = min(start_idx + page_size, len(sorted_prices))
    page_prices = sorted_prices[start_idx:end_idx]
    has_more = end_idx < len(sorted_prices)
    
    msg_lines = [f"💰 Oracle Prices (Top {end_idx} of {len(sorted_prices)})\n"]
    for p in page_prices:
        token = p.get("token") or {}
        tid = token.get("id")
        symbol = token.get("symbol") or token.get("name") or f"Token {tid}"
        price = p.get("priceUsd")
        if price is not None:
            if price >= 1:
                price_str = f"${price:,.2f}"
            elif price >= 0.01:
                price_str = f"${price:.4f}"
            else:
                price_str = f"${price:.8f}"
            msg_lines.append(f"• {symbol}: {price_str}")
    
    return "\n".join(msg_lines), has_more


def format_price_single(price_data: dict) -> str:
    """Format a single price for display."""
    token = price_data.get("token") or {}
    symbol = token.get("symbol") or token.get("name") or "?"
    price = price_data.get("priceUsd")
    
    if price is None:
        return f"Price not available for {symbol}"
    
    if price >= 1:
        price_str = f"${price:,.2f}"
    elif price >= 0.01:
        price_str = f"${price:.4f}"
    else:
        price_str = f"${price:.8f}"
    
    return f"💰 {symbol}: {price_str}"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "Welcome to SAI Bot!\n\n"
        "Commands:\n"
        "/trades <address> [open|closed] [btc] – View trades\n"
        "/prices [next] – Show top 10 oracle prices\n"
        "/price <symbol> – Get price for specific token\n"
        "/help – Show this help message\n"
    )
    await update.effective_message.reply_text(text)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await start(update, context)


async def send_trades_page(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    address: str,
    trades: list,
    trade_type: str,  # "open" or "closed"
    page: int = 0,
    page_size: int = 5,
    is_edit: bool = False
) -> None:
    """Send a page of trades with pagination."""
    # Format address display - handle both Nibiru and Ethereum addresses
    if address.startswith("0x"):
        # Ethereum address: show first 8 and last 6 chars
        addr_display = f"{address[:8]}...{address[-6:]}"
    else:
        # Nibiru address: show first 10 and last 6 chars
        addr_display = f"{address[:10]}...{address[-6:]}"
    
    if trade_type == "open":
        formatted_trades = [format_trade_open(t) for t in trades]
        header = f"✅ OPEN TRADES for {addr_display}"
    else:
        formatted_trades = [format_trade_closed(t) for t in trades]
        header = f"❌ CLOSED TRADES for {addr_display}"
    
    start_idx = page * page_size
    end_idx = min(start_idx + page_size, len(formatted_trades))
    page_trades = formatted_trades[start_idx:end_idx]
    has_more = end_idx < len(formatted_trades)
    
    result = f"{header}\n({end_idx} of {len(formatted_trades)})\n\n" + "\n\n".join(page_trades)
    
    # Create keyboard with "Next" button if there are more pages
    reply_markup = None
    if has_more:
        callback_data = f"trades_next:{address}:{trade_type}:{page + 1}"
        keyboard = [[InlineKeyboardButton("Next →", callback_data=callback_data)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
    
    if is_edit:
        await update.callback_query.edit_message_text(result, reply_markup=reply_markup)
    else:
        await update.effective_message.reply_text(result, reply_markup=reply_markup)


async def trades_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.effective_message.reply_text(
            "Usage: /trades <wallet_address> [open|closed] [btc]\n\n"
            "Supports both Nibiru and Ethereum addresses:\n"
            "• Nibiru: nibiru1abc123...\n"
            "• Ethereum: 0x1234abcd...\n\n"
            "Examples:\n"
            "/trades nibiru1abc123...\n"
            "/trades 0x1234abcd...\n"
            "/trades nibiru1abc123... open\n"
            "/trades 0x1234abcd... closed\n"
            "/trades nibiru1abc123... btc\n"
            "/trades 0x1234abcd... open btc"
        )
        return
    
    address = context.args[0].strip()
    is_open: Optional[bool] = None
    base_symbol: Optional[str] = None
    
    # Parse arguments
    for arg in context.args[1:]:
        arg_lower = arg.strip().lower()
        if arg_lower == "open":
            is_open = True
        elif arg_lower == "closed":
            is_open = False
        else:
            # Assume it's a token symbol
            base_symbol = arg.strip().upper()
    
    try:
        gql = SaiGQLClient()
        trades = gql.fetch_trades(trader=address, is_open=is_open, limit=100, base_symbol=base_symbol)
        
        if not trades:
            status_text = "open" if is_open is True else "closed" if is_open is False else ""
            symbol_text = f" for {base_symbol}" if base_symbol else ""
            await update.effective_message.reply_text(
                f"No {status_text} trades{symbol_text} found for address: {address}"
            )
            return
        
        # Separate open and closed trades
        open_trades = [t for t in trades if t.get('isOpen', False)]
        closed_trades = [t for t in trades if not t.get('isOpen', False)]
        
        # Store in context for pagination
        context.user_data[f"trades_open_{address}"] = open_trades
        context.user_data[f"trades_closed_{address}"] = closed_trades
        
        # Send open trades first (page 0)
        if open_trades and (is_open is None or is_open is True):
            await send_trades_page(update, context, address, open_trades, "open", page=0)
        
        # Send closed trades (page 0)
        if closed_trades and (is_open is None or is_open is False):
            await send_trades_page(update, context, address, closed_trades, "closed", page=0)
        
    except Exception as e:
        logger.error(f"Error fetching trades: {e}")
        await update.effective_message.reply_text(f"Error fetching trades: {str(e)}")


async def prices_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        # Get page number from context or default to 0
        page = 0
        if context.args and context.args[0].lower() == "next":
            # Store page in user_data
            page = context.user_data.get("prices_page", 0) + 1
            context.user_data["prices_page"] = page
        
        gql = SaiGQLClient()
        prices = gql.fetch_prices(limit=200)
        text, has_more = format_prices(prices, start_idx=page * 10, page_size=10)
        
        # Create keyboard with "Next" button if there are more pages
        reply_markup = None
        if has_more:
            keyboard = [[InlineKeyboardButton("Next →", callback_data="prices_next")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.effective_message.reply_text(text, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error fetching prices: {e}")
        await update.effective_message.reply_text(f"Error fetching prices: {str(e)}")


async def price_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.effective_message.reply_text(
            "Usage: /price <symbol>\n\n"
            "Example: /price btc\n"
            "Example: /price eth"
        )
        return
    
    symbol = context.args[0].strip()
    
    try:
        gql = SaiGQLClient()
        price_data = gql.fetch_price_by_symbol(symbol)
        
        if not price_data:
            await update.effective_message.reply_text(f"Token '{symbol}' not found.")
            return
        
        text = format_price_single(price_data)
        await update.effective_message.reply_text(text)
    except Exception as e:
        logger.error(f"Error fetching price: {e}")
        await update.effective_message.reply_text(f"Error fetching price: {str(e)}")


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    
    await query.answer()
    
    if query.data == "prices_next":
        # Increment page
        page = context.user_data.get("prices_page", 0) + 1
        context.user_data["prices_page"] = page
        
        try:
            gql = SaiGQLClient()
            prices = gql.fetch_prices(limit=200)
            text, has_more = format_prices(prices, start_idx=page * 10, page_size=10)
            
            reply_markup = None
            if has_more:
                keyboard = [[InlineKeyboardButton("Next →", callback_data="prices_next")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(text, reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"Error fetching prices: {e}")
            await query.edit_message_text(f"Error: {str(e)}")
    
    elif query.data and query.data.startswith("trades_next:"):
        # Parse callback data: trades_next:address:type:page
        parts = query.data.split(":", 3)
        if len(parts) == 4:
            _, address, trade_type, page_str = parts
            page = int(page_str)
            
            # Get trades from context
            trades_key = f"trades_{trade_type}_{address}"
            trades = context.user_data.get(trades_key, [])
            
            if trades:
                await send_trades_page(update, context, address, trades, trade_type, page=page, is_edit=True)
            else:
                await query.edit_message_text("Trades data expired. Please run /trades again.")


def build_app() -> Application:
    load_dotenv()
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set")
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("trades", trades_cmd))
    app.add_handler(CommandHandler("prices", prices_cmd))
    app.add_handler(CommandHandler("price", price_cmd))
    app.add_handler(CallbackQueryHandler(callback_handler))
    return app


def main() -> None:
    app = build_app()
    logger.info("Starting bot...")
    app.run_polling(close_loop=False)


if __name__ == "__main__":
    main()

