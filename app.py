from flask import Flask, render_template, request, flash, redirect, url_for, jsonify
from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user,
)
from config import Config
from models import db, User, Trade, TradeAnalysis, TradingJournal, UserSettings
from forms import (
    LoginForm,
    RegistrationForm,
    TradeForm,
    QuickTradeForm,
    JournalForm,
    EditTradeForm,
    UserSettingsForm,
    BulkAnalysisForm,
)
from ai_analysis import TradingAIAnalyzer
from datetime import datetime, timedelta, date
import pandas as pd
import plotly.graph_objs as go
import plotly.utils
import json
import os
import secrets
import requests
import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq
import math
from itertools import zip_longest
from werkzeug.utils import secure_filename

# Load environment variables from .env file
try:
    from dotenv import load_dotenv

    load_dotenv()
    print("Environment variables loaded from .env file")
except ImportError:
    print("python-dotenv not installed, using system environment variables")
    pass
except Exception as e:
    print(f"Error loading .env file: {e}, using fallback configuration")
    pass

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))


# Initialize AI analyzer
ai_analyzer = TradingAIAnalyzer()

# Initialize Tradier API configuration
TRADIER_API_TOKEN = os.getenv("TRADIER_API_TOKEN")
TRADIER_API_BASE_URL = "https://api.tradier.com/v1"  # Production environment
print(f"Tradier API Base URL: {TRADIER_API_BASE_URL}")
print(f"Tradier token configured: {'Yes' if TRADIER_API_TOKEN else 'No'}")

if not TRADIER_API_TOKEN:
    print("Warning: TRADIER_API_TOKEN environment variable not set")


def get_tradier_headers():
    """Get headers for Tradier API requests"""
    if not TRADIER_API_TOKEN:
        print("Tradier API token not configured")
        return None  # Token not configured

    headers = {
        "Authorization": f"Bearer {TRADIER_API_TOKEN}",
        "Accept": "application/json",
    }
    return headers


def get_expiration_dates_tradier(symbol):
    """Return available option expiration dates from Tradier"""
    if not TRADIER_API_TOKEN:
        print("Tradier API token not configured")
        return None

    try:
        headers = get_tradier_headers()
        if not headers:
            print("Tradier API token not configured, skipping Tradier API call")
            return None

        exp_url = f"{TRADIER_API_BASE_URL}/markets/options/expirations"
        exp_params = {"symbol": symbol}

        exp_response = requests.get(exp_url, params=exp_params, headers=headers)
        if exp_response.status_code != 200:
            print(f"Error getting expirations for {symbol}: {exp_response.status_code}")
            return None

        exp_data = exp_response.json()
        if "expirations" not in exp_data or not exp_data["expirations"]:
            print(f"No expirations found for {symbol}")
            return None

        expirations = exp_data["expirations"]["date"]
        if isinstance(expirations, str):
            expirations = [expirations]

        return expirations

    except Exception as e:
        print(f"Error fetching expirations from Tradier for {symbol}: {e}")
        return None


def get_options_chain_tradier(symbol, expiration_date=None):
    """Get options chain data using Tradier API"""
    if not TRADIER_API_TOKEN:
        print("Tradier API token not configured")
        return None, None, None, None

    try:
        headers = get_tradier_headers()
        if not headers:
            print("Tradier API token not configured, skipping Tradier API call")
            return None, None, None, None

        # First get available expiration dates
        exp_url = f"{TRADIER_API_BASE_URL}/markets/options/expirations"
        exp_params = {"symbol": symbol}

        exp_response = requests.get(exp_url, params=exp_params, headers=headers)
        if exp_response.status_code != 200:
            print(f"Error getting expirations for {symbol}: {exp_response.status_code}")
            return None, None, None, None

        exp_data = exp_response.json()
        if "expirations" not in exp_data or not exp_data["expirations"]:
            print(f"No expirations found for {symbol}")
            return None, None, None, None

        expirations = exp_data["expirations"]["date"]
        if isinstance(expirations, str):
            expirations = [expirations]

        # Use provided expiration or first available
        target_date = (
            expiration_date
            if expiration_date and expiration_date in expirations
            else expirations[0]
        )

        # Get options chain for the target date
        chain_url = f"{TRADIER_API_BASE_URL}/markets/options/chains"
        chain_params = {"symbol": symbol, "expiration": target_date}

        chain_response = requests.get(chain_url, params=chain_params, headers=headers)
        if chain_response.status_code != 200:
            print(
                f"Error getting options chain for {symbol}: {chain_response.status_code}"
            )
            return None, None, None, None

        chain_data = chain_response.json()
        if "options" not in chain_data or not chain_data["options"]:
            print(f"No options data for {symbol} on {target_date}")
            return None, None, None, None

        options = chain_data["options"]["option"]
        if not isinstance(options, list):
            options = [options]

        # Separate calls and puts
        calls_data = []
        puts_data = []

        for option in options:
            option_data = {
                "strike": float(option["strike"]),
                "last": float(option.get("last", 0)) if option.get("last") else 0,
                "bid": float(option.get("bid", 0)) if option.get("bid") else 0,
                "ask": float(option.get("ask", 0)) if option.get("ask") else 0,
                "volume": int(option.get("volume", 0)) if option.get("volume") else 0,
                "open_interest": (
                    int(option.get("open_interest", 0))
                    if option.get("open_interest")
                    else 0
                ),
                "implied_volatility": (
                    float(option.get("greeks", {}).get("mid_iv", 0))
                    if option.get("greeks")
                    else 0
                ),
            }

            if option["option_type"] == "call":
                calls_data.append(option_data)
            else:
                puts_data.append(option_data)

        # Convert to DataFrames for compatibility
        calls_df = pd.DataFrame(calls_data) if calls_data else pd.DataFrame()
        puts_df = pd.DataFrame(puts_data) if puts_data else pd.DataFrame()

        # Get current stock price
        current_price, description = get_stock_price_tradier(symbol)

        return calls_df, puts_df, current_price, expirations

    except Exception as e:
        print(f"Error fetching options data from Tradier for {symbol}: {e}")
        return None, None, None, None


def get_stock_price_tradier(symbol):
    """Get current stock price and company name using Tradier API"""
    if not TRADIER_API_TOKEN:
        print("Tradier API token not configured")
        return None, None

    try:
        headers = get_tradier_headers()
        if not headers:
            print("Tradier API token not configured")
            return None, None

        url = f"{TRADIER_API_BASE_URL}/markets/quotes"
        params = {"symbols": symbol}

        print(f"Requesting stock price for {symbol} from Tradier...")
        response = requests.get(url, params=params, headers=headers)

        if response.status_code != 200:
            print(f"Tradier API error: {response.status_code} - {response.text}")
            return None, None

        data = response.json()
        print(f"Tradier response: {data}")

        if "quotes" in data and "quote" in data["quotes"]:
            quote = data["quotes"]["quote"]
            if isinstance(quote, list):
                quote = quote[0]
            price = float(quote.get("last", 0))
            description = quote.get(
                "description", symbol
            )  # Fall back to symbol if no description
            print(f"Got price for {symbol}: {price}, description: {description}")
            return price, description

        print(f"No price data found for {symbol} in Tradier response")
        return None, None

    except Exception as e:
        print(f"Error getting stock price from Tradier for {symbol}: {e}")
        import traceback

        traceback.print_exc()
        return None, None


def get_options_chain(symbol, expiration_date=None):
    """Get options chain data using Tradier API only"""
    if not TRADIER_API_TOKEN:
        print("Tradier API token not configured")
        return None, None, None

    try:
        print(f"Getting options chain for {symbol} using Tradier API...")
        calls, puts, current_price, expirations = get_options_chain_tradier(
            symbol, expiration_date
        )

        if (
            calls is not None
            and puts is not None
            and not calls.empty
            and not puts.empty
        ):
            print(f"Successfully retrieved options data from Tradier for {symbol}")
            return calls, puts, current_price

        print(f"Failed to get options data for {symbol} from Tradier")
        return None, None, None

    except Exception as e:
        print(f"Error in get_options_chain for {symbol}: {e}")
        import traceback

        traceback.print_exc()
        return None, None, None


def black_scholes(S, K, T, r, sigma, option_type="call"):
    """Calculate Black-Scholes option price"""
    try:
        # Handle edge cases
        if S <= 0 or K <= 0 or T <= 0 or sigma <= 0:
            return 0

        # Avoid division by zero in d1 calculation
        if sigma * np.sqrt(T) == 0:
            return 0

        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)

        if option_type == "call":
            price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        else:  # put
            price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

        return max(price, 0)
    except:
        return 0


def implied_volatility(price, S, K, T, r, option_type="call"):
    """Estimate implied volatility from option price."""
    if price <= 0 or S <= 0 or K <= 0 or T <= 0:
        return 0.0

    def objective(sigma):
        return black_scholes(S, K, T, r, sigma, option_type) - price

    try:
        return brentq(objective, 1e-6, 5.0, maxiter=100)
    except Exception:
        return 0.0


def calculate_greeks(S, K, T, r, sigma, option_type="call"):
    """Calculate option Greeks"""
    try:
        # Handle edge cases
        if S <= 0 or K <= 0 or T <= 0 or sigma <= 0:
            return {"delta": 0, "gamma": 0, "theta": 0, "vega": 0}

        # Avoid division by zero in d1 calculation
        if sigma * np.sqrt(T) == 0:
            return {"delta": 0, "gamma": 0, "theta": 0, "vega": 0}

        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)

        # Delta
        if option_type == "call":
            delta = norm.cdf(d1)
        else:
            delta = norm.cdf(d1) - 1

        # Gamma
        gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))

        # Theta
        if option_type == "call":
            theta = (
                -(S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T))
                - r * K * np.exp(-r * T) * norm.cdf(d2)
            ) / 365
        else:
            theta = (
                -(S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T))
                + r * K * np.exp(-r * T) * norm.cdf(-d2)
            ) / 365

        # Vega
        vega = S * norm.pdf(d1) * np.sqrt(T) / 100

        return {
            "delta": round(delta, 4),
            "gamma": round(gamma, 4),
            "theta": round(theta, 4),
            "vega": round(vega, 4),
        }
    except:
        return {"delta": 0, "gamma": 0, "theta": 0, "vega": 0}


def allowed_file(filename):
    """Check if file extension is allowed"""
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]
    )


def save_uploaded_file(file, prefix="chart"):
    """Save uploaded file with secure filename"""
    if file and allowed_file(file.filename):
        # Generate secure filename with random suffix
        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        unique_filename = f"{prefix}_{secrets.token_hex(8)}{ext}"

        # Create uploads directory if it doesn't exist
        upload_path = os.path.join(app.config["UPLOAD_FOLDER"])
        os.makedirs(upload_path, exist_ok=True)

        # Save file
        file_path = os.path.join(upload_path, unique_filename)
        file.save(file_path)
        return unique_filename
    return None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/home")
def home():
    """Public home page that redirects to the dashboard"""
    return redirect(url_for("dashboard"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash("Welcome back!", "success")
            return redirect(url_for("index"))
        flash("Invalid username or password", "danger")

    return render_template("login.html", form=form)


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        # Create default settings
        settings = UserSettings(user_id=user.id)
        db.session.add(settings)
        db.session.commit()

        flash("Registration successful! You can now log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html", form=form)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


@app.route("/dashboard")
def dashboard():
    """Dashboard page - shows basic stats and recent trades if logged in"""
    if current_user.is_authenticated:
        # Get recent trades
        recent_trades = current_user.get_recent_trades(10)

        # Get statistics
        stats = {
            "total_trades": Trade.query.filter_by(user_id=current_user.id).count(),
            "win_rate": current_user.get_win_rate(),
            "total_pnl": current_user.get_total_pnl(),
            "trades_analyzed": Trade.query.filter_by(
                user_id=current_user.id, is_analyzed=True
            ).count(),
        }

        # Get recent journal entries
        recent_journals = (
            TradingJournal.query.filter_by(user_id=current_user.id)
            .order_by(TradingJournal.journal_date.desc())
            .limit(5)
            .all()
        )

        # Check if today's journal exists
        today_journal = TradingJournal.query.filter_by(
            user_id=current_user.id, journal_date=date.today()
        ).first()

        return render_template(
            "dashboard.html",
            recent_trades=recent_trades,
            stats=stats,
            recent_journals=recent_journals,
            today_journal=today_journal,
        )
    else:
        # Show aggregate stats for guests using all available trades
        recent_trades = (
            Trade.query.order_by(Trade.entry_date.desc()).limit(10).all()
        )

        closed_trades = Trade.query.filter(Trade.exit_price.isnot(None)).all()
        win_rate = (
            len([t for t in closed_trades if t.profit_loss and t.profit_loss > 0])
            / len(closed_trades) * 100
            if closed_trades
            else 0
        )
        total_pnl = sum(t.profit_loss for t in closed_trades if t.profit_loss)

        stats = {
            "total_trades": Trade.query.count(),
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "trades_analyzed": Trade.query.filter_by(is_analyzed=True).count(),
        }

        recent_journals = (
            TradingJournal.query.order_by(TradingJournal.journal_date.desc())
            .limit(5)
            .all()
        )

        return render_template(
            "dashboard.html",
            recent_trades=recent_trades,
            stats=stats,
            recent_journals=recent_journals,
            today_journal=None,
        )


@app.route("/trades")
@login_required
def trades():
    page = request.args.get("page", 1, type=int)
    trades = (
        Trade.query.filter_by(user_id=current_user.id)
        .order_by(Trade.entry_date.desc())
        .paginate(page=page, per_page=20, error_out=False)
    )
    return render_template("trades.html", trades=trades)


@app.route("/add_trade", methods=["GET", "POST"])
def add_trade():
    """Display trade form. Login required only when saving."""
    form = TradeForm()

    if request.method == "POST" and not current_user.is_authenticated:
        flash("Please log in to save trades.", "warning")
        return redirect(url_for("login", next=url_for("add_trade")))

    if form.validate_on_submit():
        # Handle file uploads
        entry_chart_filename = None
        exit_chart_filename = None

        if form.entry_chart_image.data:
            entry_chart_filename = save_uploaded_file(
                form.entry_chart_image.data, "entry"
            )

        if form.exit_chart_image.data:
            exit_chart_filename = save_uploaded_file(form.exit_chart_image.data, "exit")

        trade = Trade(
            user_id=current_user.id,
            symbol=form.symbol.data.upper(),
            trade_type=form.trade_type.data,
            entry_date=form.entry_date.data,
            entry_price=form.entry_price.data,
            quantity=form.quantity.data,
            stop_loss=form.stop_loss.data,
            take_profit=form.take_profit.data,
            risk_amount=form.risk_amount.data,
            exit_date=form.exit_date.data,
            exit_price=form.exit_price.data,
            setup_type=form.setup_type.data,
            market_condition=form.market_condition.data,
            timeframe=form.timeframe.data,
            entry_reason=form.entry_reason.data,
            exit_reason=form.exit_reason.data,
            notes=form.notes.data,
            tags=form.tags.data,
            entry_chart_image=entry_chart_filename,
            exit_chart_image=exit_chart_filename,
            # Options-specific fields
            strike_price=form.strike_price.data,
            expiration_date=form.expiration_date.data,
            premium_paid=form.premium_paid.data,
            underlying_price_at_entry=form.underlying_price_at_entry.data,
            underlying_price_at_exit=form.underlying_price_at_exit.data,
            implied_volatility=form.implied_volatility.data,
            delta=form.delta.data,
            gamma=form.gamma.data,
            theta=form.theta.data,
            vega=form.vega.data,
            # Spread-specific fields
            long_strike=form.long_strike.data,
            short_strike=form.short_strike.data,
            long_premium=form.long_premium.data,
            short_premium=form.short_premium.data,
            net_credit=form.net_credit.data,
        )

        # Set option type from trade type
        if trade.trade_type == "option_call":
            trade.option_type = "call"
        elif trade.trade_type == "option_put":
            trade.option_type = "put"
        elif trade.trade_type in ["credit_put_spread", "credit_call_spread"]:
            trade.is_spread = True
            trade.spread_type = trade.trade_type
            trade.option_type = "put" if "put" in trade.trade_type else "call"
            # Calculate spread metrics
            trade.calculate_spread_metrics()

        # Calculate P&L if trade is closed
        trade.calculate_pnl()

        db.session.add(trade)
        db.session.commit()

        # Auto-analyze if trade is closed and user has auto-analysis enabled
        if (
            trade.exit_price
            and hasattr(current_user, "settings")
            and current_user.settings.auto_analyze_trades
        ):
            try:
                ai_analyzer.analyze_trade(trade)
                flash("Trade added and analyzed successfully!", "success")
            except:
                flash(
                    "Trade added successfully! Analysis will be done later.", "success"
                )
        else:
            flash("Trade added successfully!", "success")

        return redirect(url_for("trades"))

    return render_template("add_trade.html", form=form)


@app.route("/trade/<int:id>")
@login_required
def view_trade(id):
    trade = Trade.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    analysis = TradeAnalysis.query.filter_by(trade_id=id).first()
    return render_template("view_trade.html", trade=trade, analysis=analysis)


@app.route("/trade/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit_trade(id):
    trade = Trade.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    form = EditTradeForm(obj=trade)

    if form.validate_on_submit():
        if form.calculate_pnl.data:
            # Just calculate P&L and return to form
            form.populate_obj(trade)
            trade.calculate_pnl()
            db.session.commit()
            flash("P&L calculated!", "info")
            return render_template("edit_trade.html", form=form, trade=trade)
        elif form.submit.data:
            # Save the trade
            form.populate_obj(trade)
            trade.calculate_pnl()
            db.session.commit()
            flash("Trade updated successfully!", "success")
            return redirect(url_for("view_trade", id=trade.id))

    return render_template("edit_trade.html", form=form, trade=trade)


@app.route("/trade/<int:id>/analyze", methods=["POST"])
@login_required
def analyze_trade(id):
    trade = Trade.query.filter_by(id=id, user_id=current_user.id).first_or_404()

    try:
        analysis = ai_analyzer.analyze_trade(trade)
        if analysis:
            flash("Trade analysis completed!", "success")
        else:
            flash("Analysis failed. Please check your OpenAI API key.", "error")
    except Exception as e:
        flash(f"Analysis error: {str(e)}", "error")

    return redirect(url_for("view_trade", id=id))


@app.route("/journal")
@login_required
def journal():
    page = request.args.get("page", 1, type=int)
    journals = (
        TradingJournal.query.filter_by(user_id=current_user.id)
        .order_by(TradingJournal.journal_date.desc())
        .paginate(page=page, per_page=20, error_out=False)
    )
    return render_template("journal.html", journals=journals)


@app.route("/journal/add", methods=["GET", "POST"])
@app.route("/journal/<journal_date>/edit", methods=["GET", "POST"])
def add_edit_journal(journal_date=None):
    """Journal entry page. Login only required when saving or editing."""

    if journal_date:
        if not current_user.is_authenticated:
            flash("Please log in to edit journal entries.", "warning")
            return redirect(
                url_for(
                    "login", next=url_for("add_edit_journal", journal_date=journal_date)
                )
            )
        # Edit existing journal
        journal_date_obj = datetime.strptime(journal_date, "%Y-%m-%d").date()
        journal = TradingJournal.query.filter_by(
            user_id=current_user.id, journal_date=journal_date_obj
        ).first_or_404()
        form = JournalForm(obj=journal)
        is_edit = True
    else:
        # Add new journal
        journal = None
        form = JournalForm()
        is_edit = False

    if request.method == "POST" and not current_user.is_authenticated:
        flash("Please log in to save journal entries.", "warning")
        return redirect(url_for("login", next=url_for("add_edit_journal")))

    if form.validate_on_submit():
        if journal:
            # Update existing
            form.populate_obj(journal)
        else:
            # Create new
            journal = TradingJournal(user_id=current_user.id)
            form.populate_obj(journal)

        # Get trades for this day and analyze daily performance
        day_trades = journal.get_day_trades()
        if day_trades or journal.daily_pnl:
            try:
                daily_analysis = ai_analyzer.analyze_daily_performance(
                    journal, day_trades
                )
                if daily_analysis:
                    journal.ai_daily_feedback = daily_analysis["feedback"]
                    journal.daily_score = daily_analysis["daily_score"]
            except:
                pass  # Continue without AI analysis if it fails

        db.session.add(journal)
        db.session.commit()

        action = "updated" if is_edit else "added"
        flash(f"Journal entry {action} successfully!", "success")
        return redirect(url_for("journal"))

    # Get trades for this day (for context)
    if journal_date:
        day_trades = journal.get_day_trades()
    else:
        day_trades = []

    return render_template(
        "add_edit_journal.html",
        form=form,
        journal=journal,
        is_edit=is_edit,
        day_trades=day_trades,
    )


@app.route("/analytics")
@login_required
def analytics():
    # Get all closed trades for analysis
    closed_trades = (
        Trade.query.filter_by(user_id=current_user.id)
        .filter(Trade.exit_price.isnot(None))
        .all()
    )

    if not closed_trades:
        return render_template(
            "analytics.html", no_data=True, charts_json=None, stats=None
        )

    # Create analytics data
    df = pd.DataFrame(
        [
            {
                "date": trade.exit_date,
                "symbol": trade.symbol,
                "pnl": trade.profit_loss or 0,
                "pnl_percent": trade.profit_loss_percent or 0,
                "setup_type": trade.setup_type,
                "timeframe": trade.timeframe,
                "is_winner": trade.is_winner(),
            }
            for trade in closed_trades
        ]
    )

    # Calculate statistics
    stats = {
        "total_trades": len(closed_trades),
        "winning_trades": len([t for t in closed_trades if t.is_winner()]),
        "losing_trades": len(
            [t for t in closed_trades if t.profit_loss and t.profit_loss < 0]
        ),
        "win_rate": len([t for t in closed_trades if t.is_winner()])
        / len(closed_trades)
        * 100,
        "total_pnl": sum(t.profit_loss for t in closed_trades if t.profit_loss),
        "avg_win": df[df["pnl"] > 0]["pnl"].mean() if len(df[df["pnl"] > 0]) > 0 else 0,
        "avg_loss": (
            df[df["pnl"] < 0]["pnl"].mean() if len(df[df["pnl"] < 0]) > 0 else 0
        ),
        "largest_win": df["pnl"].max(),
        "largest_loss": df["pnl"].min(),
        "profit_factor": (
            abs(df[df["pnl"] > 0]["pnl"].sum() / df[df["pnl"] < 0]["pnl"].sum())
            if df[df["pnl"] < 0]["pnl"].sum() != 0
            else 0
        ),
    }

    # Create charts
    charts = create_analytics_charts(df)
    charts_json = json.dumps(charts, cls=plotly.utils.PlotlyJSONEncoder)

    return render_template(
        "analytics.html", charts_json=charts_json, stats=stats, no_data=False
    )


def create_analytics_charts(df):
    """Create analytics charts"""
    charts = {}

    # P&L over time
    df_sorted = df.sort_values("date")
    df_sorted["cumulative_pnl"] = df_sorted["pnl"].cumsum()

    charts["pnl_over_time"] = {
        "data": [
            {
                "x": df_sorted["date"].tolist(),
                "y": df_sorted["cumulative_pnl"].tolist(),
                "type": "scatter",
                "mode": "lines",
                "name": "Cumulative P&L",
                "line": {"color": "#1f77b4"},
            }
        ],
        "layout": {
            "title": "Cumulative P&L Over Time",
            "xaxis": {"title": "Date"},
            "yaxis": {"title": "Cumulative P&L ($)"},
            "height": 400,
        },
    }

    # Win/Loss distribution
    win_loss_counts = df["is_winner"].value_counts()
    charts["win_loss_pie"] = {
        "data": [
            {
                "values": [win_loss_counts.get(True, 0), win_loss_counts.get(False, 0)],
                "labels": ["Wins", "Losses"],
                "type": "pie",
                "colors": ["#2ecc71", "#e74c3c"],
            }
        ],
        "layout": {"title": "Win/Loss Distribution", "height": 400},
    }

    # Setup type performance
    setup_performance = (
        df.groupby("setup_type")["pnl"].sum().sort_values(ascending=False)
    )
    charts["setup_performance"] = {
        "data": [
            {
                "x": setup_performance.index.tolist(),
                "y": setup_performance.values.tolist(),
                "type": "bar",
                "marker": {
                    "color": [
                        "#2ecc71" if x > 0 else "#e74c3c"
                        for x in setup_performance.values
                    ]
                },
            }
        ],
        "layout": {
            "title": "P&L by Setup Type",
            "xaxis": {"title": "Setup Type"},
            "yaxis": {"title": "Total P&L ($)"},
            "height": 400,
        },
    }

    return charts


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    user_settings = current_user.settings
    if not user_settings:
        user_settings = UserSettings(user_id=current_user.id)
        db.session.add(user_settings)
        db.session.commit()

    form = UserSettingsForm(obj=user_settings)

    if form.validate_on_submit():
        form.populate_obj(user_settings)

        # Also update user account size if provided
        if form.account_size.data:
            current_user.account_size = form.account_size.data
        if form.default_risk_percent.data:
            current_user.default_risk_percent = form.default_risk_percent.data

        db.session.commit()
        flash("Settings updated successfully!", "success")
        return redirect(url_for("settings"))

    return render_template("settings.html", form=form)


@app.route("/bulk_analysis", methods=["GET", "POST"])
@login_required
def bulk_analysis():
    form = BulkAnalysisForm()

    # Populate trade choices for individual analysis
    trades = (
        Trade.query.filter_by(user_id=current_user.id)
        .filter(Trade.exit_price.isnot(None))
        .order_by(Trade.entry_date.desc())
        .all()
    )
    form.trade_id.choices = [
        (0, "Select a trade...")
    ] + [
        (t.id, f"{t.symbol} - {t.entry_date.strftime('%Y-%m-%d')}") for t in trades
    ]

    if form.validate_on_submit():
        # Handle individual trade analysis first
        if form.trade_id.data and form.trade_id.data != 0:
            trade = Trade.query.filter_by(
                id=form.trade_id.data, user_id=current_user.id
            ).first()
            if trade:
                try:
                    ai_analyzer.analyze_trade(trade)
                    flash("Trade analyzed successfully!", "success")
                except Exception as e:
                    flash(f"Analysis failed: {str(e)}", "error")
                return redirect(url_for("view_trade", id=trade.id))

        trades_to_analyze = []

        if form.analyze_all_unanalyzed.data:
            trades_to_analyze.extend(
                Trade.query.filter_by(user_id=current_user.id, is_analyzed=False)
                .filter(Trade.exit_price.isnot(None))
                .all()
            )

        if form.analyze_recent.data:
            thirty_days_ago = datetime.now() - timedelta(days=30)
            recent_trades = (
                Trade.query.filter_by(user_id=current_user.id)
                .filter(Trade.entry_date >= thirty_days_ago)
                .filter(Trade.exit_price.isnot(None))
                .all()
            )
            trades_to_analyze.extend(recent_trades)

        # Remove duplicates
        trades_to_analyze = list(set(trades_to_analyze))

        success_count = 0
        for trade in trades_to_analyze:
            try:
                ai_analyzer.analyze_trade(trade)
                success_count += 1
            except:
                continue

        flash(
            f"Successfully analyzed {success_count} out of {len(trades_to_analyze)} trades.",
            "success",
        )
        return redirect(url_for("trades"))

    # Get counts for display
    unanalyzed_count = (
        Trade.query.filter_by(user_id=current_user.id, is_analyzed=False)
        .filter(Trade.exit_price.isnot(None))
        .count()
    )

    thirty_days_ago = datetime.now() - timedelta(days=30)
    recent_count = (
        Trade.query.filter_by(user_id=current_user.id)
        .filter(Trade.entry_date >= thirty_days_ago)
        .filter(Trade.exit_price.isnot(None))
        .count()
    )

    return render_template(
        "bulk_analysis.html",
        form=form,
        unanalyzed_count=unanalyzed_count,
        recent_count=recent_count,
    )


@app.route("/api/quick_trade", methods=["POST"])
@login_required
def api_quick_trade():
    """API endpoint for quick trade entry"""
    form = QuickTradeForm()

    if form.validate_on_submit():
        trade = Trade(
            user_id=current_user.id,
            symbol=form.symbol.data.upper(),
            trade_type=form.trade_type.data,
            entry_date=datetime.now(),
            entry_price=form.entry_price.data,
            quantity=form.quantity.data,
            setup_type=form.setup_type.data,
            timeframe="day_trade",  # Default for quick trades
        )

        db.session.add(trade)
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": "Trade added successfully!",
                "trade_id": trade.id,
            }
        )

    return jsonify({"success": False, "errors": form.errors})


@app.route("/tools")
def tools():
    """Tools and calculators main page"""
    return render_template("tools/index.html")


@app.route("/tools/options-calculator", methods=["GET", "POST"])
def options_calculator():
    """Options calculator with Tradier data only"""
    context = {
        "symbol": None,
        "current_price": None,
        "options_data": None,
        "expiration_dates": None,
        "selected_date": None,
        "stock_name": None,
        "calls": None,
        "puts": None,
    }

    if request.method == "POST":
        symbol = request.form.get("symbol", "").upper()
        expiration_date = request.form.get("expiration_date")
        context["symbol"] = symbol

        if symbol:
            try:
                # Get current price from Tradier
                current_price, description = get_stock_price_tradier(symbol)
                stock_name = description  # Use description as stock name

                if not current_price:
                    print(f"Could not get current price for {symbol} from Tradier")
                    flash(
                        f"Error: Could not get current price for {symbol}. Please check your Tradier API token.",
                        "danger",
                    )
                    return render_template(
                        "tools/options_calculator.html", context=context
                    )

                context["stock_name"] = stock_name
                context["current_price"] = current_price

                # Always fetch available expiration dates first
                expirations = get_expiration_dates_tradier(symbol)
                if expirations:
                    context["expiration_dates"] = expirations

                if expiration_date:
                    # If user selected a date, fetch chain for that date
                    calls, puts, price, _ = get_options_chain_tradier(
                        symbol, expiration_date
                    )

                    if (
                        calls is not None
                        and puts is not None
                        and not calls.empty
                        and not puts.empty
                    ):
                        # Sort by strike to ensure correct ordering
                        calls_sorted = calls.sort_values("strike")
                        puts_sorted = puts.sort_values("strike")

                        context["calls"] = calls_sorted.to_dict("records")
                        context["puts"] = puts_sorted.to_dict("records")
                        context["selected_date"] = expiration_date

                        # Combine calls and puts so template can iterate safely even if lengths differ
                        options_rows = []
                        for c, p in zip_longest(context["calls"], context["puts"]):
                            options_rows.append({"call": c, "put": p})
                        context["options_rows"] = options_rows
                    else:
                        flash(
                            "Error: Could not get options data from Tradier. Please check your API token.",
                            "danger",
                        )
                else:
                    # If no date selected yet, don't populate chain
                    context["selected_date"] = None

            except Exception as e:
                print(f"Error in options calculator: {e}")
                flash(f"Error: {str(e)}", "danger")

    return render_template("tools/options_calculator.html", context=context)


@app.route("/tools/options-pnl", methods=["POST"])
def calculate_options_pnl():
    """Calculate comprehensive options P&L analysis"""
    try:
        data = request.get_json()

        option_type = data.get("option_type")  # 'call' or 'put'
        strike = float(data.get("strike"))
        current_price = float(data.get("current_price"))
        expiration_date = data.get("expiration_date")
        premium = float(data.get("premium", 0))
        quantity = int(data.get("quantity", 1))

        # Calculate days to expiration
        exp_date = datetime.strptime(expiration_date, "%Y-%m-%d").date()
        days_to_exp = (exp_date - datetime.now().date()).days
        if days_to_exp <= 0:
            return jsonify({"success": False, "error": "Option already expired"})

        # Convert to years for pricing models
        time_to_exp = days_to_exp / 365.0

        # Calculate time points starting at 100% of time remaining
        fractions = [1.0, 0.75, 0.5, 0.25, 0.0]
        # Round to whole days, remove duplicates, and sort descending
        time_points = sorted(
            {max(0, int(round(days_to_exp * f))) for f in fractions},
            reverse=True,
        )

        # Estimate implied volatility from the option's market price
        implied_vol = 0.2
        if premium > 0 and strike > 0 and days_to_exp > 0:
            est_iv = implied_volatility(
                premium, current_price, strike, time_to_exp, 0.02, option_type
            )
            if est_iv > 0:
                implied_vol = est_iv

        # Calculate price scenarios spanning below current price and
        # extending past the strike price to properly show profits for
        # far OTM options moving in-the-money
        min_price = min(current_price, strike) * 0.85
        max_price = max(current_price, strike) * 1.15
        price_steps = [round(p, 2) for p in np.linspace(min_price, max_price, 7)]
        time_slices = [
            round(t, 3)
            for t in [
                time_to_exp,
                max(time_to_exp * 0.75, 1 / 365),
                max(time_to_exp * 0.50, 1 / 365),
                max(time_to_exp * 0.25, 1 / 365),
                0,
            ]
        ]

        pnl_rows = []
        for Px in price_steps:
            row = {"stock_price": Px, "time_data": []}
            for t in time_slices:
                if t == 0:
                    # At expiration use intrinsic value instead of Black-Scholes
                    if option_type == "call":
                        theo = max(Px - strike, 0)
                    else:
                        theo = max(strike - Px, 0)
                else:
                    theo = black_scholes(Px, strike, t, 0.02, implied_vol, option_type)
                pnl = (theo - premium) * quantity * 100

                ret_pct = (pnl / (premium * quantity * 100)) * 100 if premium else 0
                row["time_data"].append({
                    "pnl": round(pnl, 2),
                    "return_percent": round(ret_pct, 2)
                })
            pnl_rows.append(row)



        # Create the analysis object
        analysis = {
            "option_info": {
                "type": option_type,
                "strike": strike,
                "premium": premium,
                "days_to_expiration": days_to_exp,
                "implied_volatility": round(implied_vol * 100, 2),
                "time_points": time_points,
                "center_price": round(current_price, 2),
                "standard_deviation": round(implied_vol * current_price, 2),
            },

            "pnl_data": pnl_rows,

        }

        return jsonify({"success": True, "analysis": analysis})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/tools/black-scholes")
def black_scholes_calculator():
    """Black-Scholes options pricing calculator"""
    return render_template("tools/black_scholes.html")


@app.route("/tools/calculate-bs", methods=["POST"])
def calculate_black_scholes():
    """Calculate Black-Scholes price and Greeks"""
    try:
        data = request.get_json()

        S = float(data.get("stock_price"))
        K = float(data.get("strike_price"))
        T = float(data.get("time_to_expiration")) / 365.0
        r = float(data.get("risk_free_rate")) / 100.0
        sigma = float(data.get("volatility")) / 100.0
        option_type = data.get("option_type")

        # Calculate price
        price = black_scholes(S, K, T, r, sigma, option_type)

        # Calculate Greeks
        greeks = calculate_greeks(S, K, T, r, sigma, option_type)

        return jsonify({"success": True, "price": round(price, 4), "greeks": greeks})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/tools/stock-lookup")
def stock_lookup():
    """Stock information lookup tool"""
    return render_template("tools/stock_lookup.html")


@app.route("/search_stocks")
def search_stocks():
    """Search for stock symbols and company names - comprehensive options-enabled stocks"""
    query = request.args.get("q", "").strip().upper()

    if len(query) < 1:
        return jsonify([])

    # List of most common stocks to prioritize
    most_common = [
        "AAPL",
        "MSFT",
        "SPY",
        "TSLA",
        "NVDA",
        "AMZN",
        "GOOGL",
        "META",
        "QQQ",
        "JPM",
        "V",
        "MA",
        "BAC",
        "NFLX",
        "AMD",
        "DIS",
        "WMT",
        "BRK.B",
        "XOM",
        "UNH",
        "VTI",
        "VOO",
        "IWM",
        "DIA",
        "GS",
        "PYPL",
        "COST",
        "HD",
        "T",
        "PFE",
        "MRK",
        "KO",
        "PEP",
        "MCD",
        "NKE",
        "SBUX",
        "INTC",
        "CSCO",
        "ORCL",
        "CRM",
        "ADBE",
        "IBM",
        "TXN",
        "QCOM",
        "MU",
        "WFC",
        "C",
        "AXP",
        "MS",
        "GME",
        "AMC",
        "BB",
        "NOK",
        "F",
        "GE",
        "PLTR",
        "NIO",
        "RIOT",
        "MARA",
    ]

    # Extended stock database with name mappings
    stocks_db = [
        {"symbol": "AAPL", "name": "Apple Inc"},
        {"symbol": "MSFT", "name": "Microsoft Corporation"},
        {"symbol": "SPY", "name": "SPDR S&P 500 ETF Trust"},
        {"symbol": "TSLA", "name": "Tesla Inc"},
        {"symbol": "NVDA", "name": "NVIDIA Corporation"},
        {"symbol": "AMZN", "name": "Amazon.com Inc"},
        {"symbol": "GOOGL", "name": "Alphabet Inc Class A"},
        {"symbol": "META", "name": "Meta Platforms Inc"},
        {"symbol": "QQQ", "name": "Invesco QQQ Trust"},
        {"symbol": "JPM", "name": "JPMorgan Chase & Co"},
        {"symbol": "V", "name": "Visa Inc"},
        {"symbol": "MA", "name": "Mastercard Incorporated"},
        {"symbol": "BAC", "name": "Bank of America Corporation"},
        {"symbol": "NFLX", "name": "Netflix Inc"},
        {"symbol": "AMD", "name": "Advanced Micro Devices Inc"},
        {"symbol": "DIS", "name": "The Walt Disney Company"},
        {"symbol": "WMT", "name": "Walmart Inc"},
        {"symbol": "BRK.B", "name": "Berkshire Hathaway Inc Class B"},
        {"symbol": "XOM", "name": "Exxon Mobil Corporation"},
        {"symbol": "UNH", "name": "UnitedHealth Group Incorporated"},
        {"symbol": "VTI", "name": "Vanguard Total Stock Market ETF"},
        {"symbol": "VOO", "name": "Vanguard S&P 500 ETF"},
        {"symbol": "IWM", "name": "iShares Russell 2000 ETF"},
        {"symbol": "DIA", "name": "SPDR Dow Jones Industrial Average ETF Trust"},
        {"symbol": "GS", "name": "The Goldman Sachs Group Inc"},
        {"symbol": "PYPL", "name": "PayPal Holdings Inc"},
        {"symbol": "COST", "name": "Costco Wholesale Corporation"},
        {"symbol": "HD", "name": "The Home Depot Inc"},
        {"symbol": "T", "name": "AT&T Inc"},
        {"symbol": "PFE", "name": "Pfizer Inc"},
        {"symbol": "MRK", "name": "Merck & Co Inc"},
        {"symbol": "KO", "name": "The Coca-Cola Company"},
        {"symbol": "PEP", "name": "PepsiCo Inc"},
        {"symbol": "MCD", "name": "McDonald's Corporation"},
        {"symbol": "NKE", "name": "NIKE Inc"},
        {"symbol": "SBUX", "name": "Starbucks Corporation"},
        {"symbol": "INTC", "name": "Intel Corporation"},
        {"symbol": "CSCO", "name": "Cisco Systems Inc"},
        {"symbol": "ORCL", "name": "Oracle Corporation"},
        {"symbol": "CRM", "name": "Salesforce Inc"},
        {"symbol": "ADBE", "name": "Adobe Inc"},
        {"symbol": "IBM", "name": "International Business Machines Corporation"},
        {"symbol": "TXN", "name": "Texas Instruments Incorporated"},
        {"symbol": "QCOM", "name": "QUALCOMM Incorporated"},
        {"symbol": "MU", "name": "Micron Technology Inc"},
        {"symbol": "WFC", "name": "Wells Fargo & Company"},
        {"symbol": "C", "name": "Citigroup Inc"},
        {"symbol": "AXP", "name": "American Express Company"},
        {"symbol": "MS", "name": "Morgan Stanley"},
        {"symbol": "GME", "name": "GameStop Corp"},
        {"symbol": "AMC", "name": "AMC Entertainment Holdings Inc"},
        {"symbol": "BB", "name": "BlackBerry Limited"},
        {"symbol": "NOK", "name": "Nokia Corporation"},
        {"symbol": "F", "name": "Ford Motor Company"},
        {"symbol": "GE", "name": "General Electric Company"},
        {"symbol": "PLTR", "name": "Palantir Technologies Inc"},
        {"symbol": "NIO", "name": "NIO Inc"},
        {"symbol": "RIOT", "name": "Riot Platforms Inc"},
        {"symbol": "MARA", "name": "Marathon Digital Holdings Inc"},
        {"symbol": "AA", "name": "Alcoa Corp"},
        {"symbol": "BA", "name": "Boeing Co"},
    ]

    # Find matches
    matches = []

    # Prioritize exact symbol matches from most common list
    for stock in stocks_db:
        if stock["symbol"] in most_common and stock["symbol"].startswith(query):
            matches.append(stock)

    # Add partial symbol matches
    for stock in stocks_db:
        if stock not in matches and query in stock["symbol"]:
            matches.append(stock)

    # Add name matches
    for stock in stocks_db:
        if stock not in matches and query in stock["name"].upper():
            matches.append(stock)

    # Limit results to 15 for performance
    matches = matches[:15]

    # Format for jQuery UI autocomplete
    results = []
    for stock in matches:
        results.append(
            {"label": f"{stock['symbol']} — {stock['name']}", "value": stock["symbol"]}
        )

    return jsonify(results)


@app.route("/test-options/<symbol>")
def test_options(symbol):
    """Test endpoint to debug options chain issues"""
    symbol = symbol.upper()
    print(f"Testing options for {symbol}")

    # Test Tradier API
    result = {
        "symbol": symbol,
        "tradier_configured": TRADIER_API_TOKEN != "your_tradier_token_here"
        and TRADIER_API_TOKEN,
        "tradier_result": None,
        "errors": [],
    }

    # Test Tradier API
    try:
        calls, puts, price, expirations = get_options_chain_tradier(symbol)
        result["tradier_result"] = {
            "success": calls is not None and puts is not None,
            "calls_count": len(calls) if calls is not None else 0,
            "puts_count": len(puts) if puts is not None else 0,
            "current_price": price,
            "expiration_count": len(expirations) if expirations else 0,
        }
    except Exception as e:
        result["errors"].append(f"Tradier error: {str(e)}")

    return jsonify(result)


# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template("500.html"), 500


if __name__ == "__main__":
    app.run(debug=True)
