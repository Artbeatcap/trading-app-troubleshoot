#!/usr/bin/env python3
"""
Test script to verify options trading functionality
"""

from app import app
from models import db, User, Trade
from datetime import datetime, date

def test_options_functionality():
    """Test options trade creation and calculations"""
    with app.app_context():
        print("🧪 Testing Options Trading Functionality...")
        
        # Create test user if doesn't exist
        test_user = User.query.filter_by(username='test_options').first()
        if not test_user:
            test_user = User(username='test_options', email='test@example.com')
            test_user.set_password('password')
            db.session.add(test_user)
            db.session.commit()
            print("✅ Created test user")
        
        # Test options trade creation
        test_trade = Trade(
            user_id=test_user.id,
            symbol='AAPL',
            trade_type='option_call',
            entry_date=datetime.now(),
            entry_price=2.50,  # Premium paid
            quantity=10,  # 10 contracts
            strike_price=150.00,
            expiration_date=date(2024, 12, 20),
            premium_paid=2.50,
            underlying_price_at_entry=148.00,
            underlying_price_at_exit=155.00,
            implied_volatility=25.5,
            delta=0.65,
            gamma=0.05,
            theta=-0.15,
            vega=0.25,
            exit_price=4.00,  # Sold for $4.00
            setup_type='breakout',
            timeframe='swing',
            entry_reason='Expected earnings-driven breakout above $150 resistance'
        )
        
        # Set option type
        test_trade.option_type = 'call'
        
        # Calculate P&L
        test_trade.calculate_pnl()
        
        db.session.add(test_trade)
        db.session.commit()
        
        print(f"✅ Created options trade: {test_trade.symbol}")
        print(f"   • Trade Type: {test_trade.trade_type}")
        print(f"   • Strike Price: ${test_trade.strike_price}")
        print(f"   • Expiration: {test_trade.expiration_date}")
        print(f"   • Premium Paid: ${test_trade.premium_paid}")
        print(f"   • Moneyness: {test_trade.get_moneyness()}")
        print(f"   • Days to Expiration: {test_trade.get_days_to_expiration()}")
        print(f"   • Intrinsic Value: ${test_trade.get_intrinsic_value()}")
        print(f"   • Time Value: ${test_trade.get_time_value()}")
        print(f"   • P&L: ${test_trade.profit_loss}")
        print(f"   • P&L %: {test_trade.profit_loss_percent:.2f}%")
        print(f"   • Contract Multiplier: {test_trade.get_contract_multiplier()}")
        
        # Test to_dict method includes options data
        trade_dict = test_trade.to_dict()
        options_fields = ['is_option_trade', 'strike_price', 'expiration_date', 'moneyness', 'intrinsic_value', 'time_value']
        missing_fields = [field for field in options_fields if field not in trade_dict]
        
        if missing_fields:
            print(f"❌ Missing fields in to_dict(): {missing_fields}")
        else:
            print("✅ All options fields present in to_dict()")
        
        print("\n🎉 Options functionality test completed successfully!")
        return test_trade

if __name__ == "__main__":
    test_options_functionality() 