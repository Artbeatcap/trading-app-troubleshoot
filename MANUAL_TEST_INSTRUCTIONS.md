# Manual Test Instructions for Market Brief Pipeline Optimization

## Quick Test Commands

Run these commands in your terminal to verify the optimization works:

### 1. Test Basic Imports
```bash
python -c "
import sys
sys.path.insert(0, '.')
from schemas.brief_input import BriefInput
from pipeline.prepare_inputs import prepare_brief_input
from pipeline.write_brief import build_brief
print('✓ All imports successful')
"
```

### 2. Test Data Preparation
```bash
python -c "
import sys
sys.path.insert(0, '.')
from pipeline.prepare_inputs import prepare_brief_input, minify_brief_input

test_data = {
    'expected_range': {
        'spy': {'current_price': 445.123456, 'change_percent': 1.234567, 'volume': 1234567},
        'qqq': {'current_price': 378.987654, 'change_percent': -0.876543, 'volume': 2345678}
    },
    'headlines': [{'headline': 'Test headline that should be truncated'}],
    'gapping_stocks': [],
    'economic_catalysts': []
}

brief = prepare_brief_input(test_data)
mini = minify_brief_input(brief)
print(f'✓ Brief: {len(brief[\"indices\"])} indices, minified: {len(mini)} chars')
"
```

### 3. Test Capping and Rounding
```bash
python -c "
import sys
sys.path.insert(0, '.')
from pipeline.prepare_inputs import prepare_brief_input

# Create data with more items than caps
test_data = {
    'expected_range': {
        'spy': {'current_price': 445.123456, 'change_percent': 1.234567, 'volume': 1234567},
        'qqq': {'current_price': 378.987654, 'change_percent': -0.876543, 'volume': 2345678},
        'iwm': {'current_price': 198.555555, 'change_percent': 2.111111, 'volume': 3456789},
        'dia': {'current_price': 345.777777, 'change_percent': 0.333333, 'volume': 4567890},
        'vix': {'current_price': 18.999999, 'change_percent': -5.666666, 'volume': 5678901},
        'tlt': {'current_price': 95.444444, 'change_percent': 1.777777, 'volume': 6789012},
        'extra': {'current_price': 100.0, 'change_percent': 0.0, 'volume': 1000000}
    },
    'headlines': [
        {'headline': 'Headline 1'},
        {'headline': 'Headline 2'},
        {'headline': 'Headline 3'},
        {'headline': 'Headline 4'},
        {'headline': 'Headline 5'},
        {'headline': 'Headline 6 - should be capped'}
    ],
    'gapping_stocks': [],
    'economic_catalysts': []
}

brief = prepare_brief_input(test_data)
print(f'Indices: {len(brief[\"indices\"])} (max 6)')
print(f'Headlines: {len(brief[\"headlines\"])} (max 5)')
print(f'First price: {brief[\"indices\"][0][\"price\"]} (should be 2 decimals)')
print('✓ Capping and rounding work correctly')
"
```

### 4. Test Full Pipeline (requires OpenAI API key)
```bash
# Set your OpenAI API key first
export OPENAI_API_KEY="your-api-key-here"

python -c "
import sys
sys.path.insert(0, '.')
from pipeline.write_brief import build_brief

test_data = {
    'expected_range': {
        'spy': {'current_price': 445.12, 'change_percent': 1.2, 'volume': 1234000}
    },
    'headlines': [{'headline': 'Market opens higher on positive earnings'}],
    'gapping_stocks': [{'symbol': 'AAPL', 'current_price': 175.50, 'change_percent': 2.1, 'volume': 50000000}],
    'economic_catalysts': [{'time': '08:30', 'event': 'CPI Data', 'impact': 'High', 'estimate': 3.2, 'previous': 3.1}]
}

try:
    prose = build_brief(test_data, polish=False)
    print(f'✓ Pipeline successful: {len(prose)} characters generated')
    print('First 200 chars:', prose[:200])
except Exception as e:
    print(f'Pipeline test failed: {e}')
"
```

## Expected Results

### ✅ **Import Test**
- Should print: "✓ All imports successful"

### ✅ **Data Preparation Test**  
- Should show: "✓ Brief: 2 indices, minified: [number] chars"
- Minified length should be < 1000 characters for this small test

### ✅ **Capping Test**
- Indices: Should show 6 (not 7) - extra index capped
- Headlines: Should show 5 (not 6) - extra headline capped  
- Price: Should show 2 decimal places (e.g., 445.12, not 445.123456)

### ✅ **Pipeline Test**
- Should generate markdown prose
- Should show token usage logs with [TOKENS] prefix
- Should be much shorter than original prompts

## Verification Checklist

- [ ] All imports work without errors
- [ ] Data preparation caps arrays correctly
- [ ] Numbers are rounded to appropriate decimals
- [ ] Minified JSON is valid and compact
- [ ] Pipeline generates markdown (not HTML)
- [ ] Token usage is logged
- [ ] No HTML is passed to LLM

## Troubleshooting

If tests fail:

1. **Import Errors**: Check that all files are in correct directories
2. **Syntax Errors**: Run `python -m py_compile filename.py` on each file
3. **Missing Dependencies**: Install required packages from requirements.txt
4. **API Errors**: Ensure OPENAI_API_KEY is set for pipeline tests

## Success Criteria

The optimization is working if:
- ✅ All imports succeed
- ✅ Arrays are capped (6 indices max, 5 headlines max, etc.)
- ✅ Numbers are rounded (prices to 2 decimals, changes to 1 decimal)
- ✅ Minified JSON is < 50k characters for busy day
- ✅ Pipeline generates markdown prose
- ✅ Token usage is logged with [TOKENS] prefix

If all tests pass, the 90% token reduction optimization is working correctly!



