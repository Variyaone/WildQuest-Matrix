"""
LaTeX Formula to Python Code Converter

Convert LaTeX mathematical formulas to executable Python code using LLM.
"""

import os
import re
import json
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ConversionResult:
    success: bool
    python_code: str
    formula: str
    error: Optional[str] = None
    variables: Optional[Dict[str, str]] = None


LATEX_PATTERNS = [
    r'\\frac',
    r'\\sum',
    r'\\int',
    r'\\prod',
    r'\\sqrt',
    r'\\alpha',
    r'\\beta',
    r'\\gamma',
    r'\\delta',
    r'\\begin{',
    r'\\end{',
    r'\\left',
    r'\\right',
    r'\\log',
    r'\\exp',
    r'\\sigma',
    r'\\mu',
    r'\\rho',
]


def is_latex_formula(formula: str) -> bool:
    for pattern in LATEX_PATTERNS:
        if re.search(pattern, formula, re.IGNORECASE):
            return True
    return False


def convert_latex_to_python(
    formula: str,
    description: str = "",
    variables: Optional[Dict[str, str]] = None,
    model: str = "gpt-4o-mini"
) -> ConversionResult:
    """
    Convert LaTeX formula to Python code using LLM.
    
    Args:
        formula: LaTeX formula string
        description: Factor description for context
        variables: Variable definitions
        model: LLM model to use
    
    Returns:
        ConversionResult with python_code or error
    """
    if not is_latex_formula(formula):
        return ConversionResult(
            success=True,
            python_code=formula,
            formula=formula,
            variables=variables
        )
    
    try:
        import openai
    except ImportError:
        return ConversionResult(
            success=False,
            python_code="",
            formula=formula,
            error="openai package not installed. Run: pip install openai"
        )
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return ConversionResult(
            success=False,
            python_code="",
            formula=formula,
            error="OPENAI_API_KEY not set"
        )
    
    api_base = os.getenv("OPENAI_API_BASE")
    
    client = openai.OpenAI(
        api_key=api_key,
        base_url=api_base if api_base else None
    )
    
    var_desc = ""
    if variables:
        var_desc = "\n".join([f"  - {k}: {v}" for k, v in variables.items()])
    
    prompt = f"""You are a quantitative finance expert. Convert the following LaTeX formula to executable Python code for stock factor calculation.

**LaTeX Formula:**
{formula}

**Description:**
{description}

**Variables:**
{var_desc if var_desc else "No specific variable definitions provided"}

**Requirements:**
1. Output ONLY the Python function code, no explanations
2. The function should take a pandas DataFrame `df` as input
3. The DataFrame contains columns: close, open, high, low, volume, date, stock_code
4. Return a pandas Series with the factor values
5. Handle NaN values appropriately
6. Use vectorized operations (pandas/numpy) for performance
7. For time-series operations, use rolling windows or shift

**Output format:**
```python
def calculate_factor(df):
    # Your implementation
    return factor_values
```

**Common mappings:**
- P_i,t or P_{i,t} -> df['close'] (price at time t)
- P_i,t-1 -> df['close'].shift(1)
- r_i,t -> df['close'].pct_change()
- ME_i,t -> market cap (if not available, use close * volume as proxy)
- B_i,t -> book value (if not available, use a proxy)
- N -> number of stocks (len of DataFrame)
- \\frac{{a}}{{b}} -> a / b
- \\sum_{{i=1}}^{{N}} x_i -> x.sum()
- \\log(x) -> np.log(x)
- \\sqrt{{x}} -> np.sqrt(x)

Now convert the formula:"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a quantitative finance expert specializing in converting mathematical formulas to Python code."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=1000
        )
        
        content = response.choices[0].message.content.strip()
        
        code_match = re.search(r'```python\s*(.*?)\s*```', content, re.DOTALL)
        if code_match:
            python_code = code_match.group(1).strip()
        else:
            code_match = re.search(r'```\s*(.*?)\s*```', content, re.DOTALL)
            if code_match:
                python_code = code_match.group(1).strip()
            else:
                python_code = content
        
        if 'def calculate_factor' not in python_code:
            python_code = f"def calculate_factor(df):\n    return {python_code}"
        
        compile(python_code, '<string>', 'exec')
        
        return ConversionResult(
            success=True,
            python_code=python_code,
            formula=formula,
            variables=variables
        )
        
    except Exception as e:
        logger.error(f"LaTeX conversion failed: {e}")
        return ConversionResult(
            success=False,
            python_code="",
            formula=formula,
            error=str(e)
        )


def convert_factor_to_code(
    name: str,
    formula: str,
    description: str = "",
    variables: Optional[Dict[str, str]] = None,
    model: str = "gpt-4o-mini"
) -> Tuple[bool, str, str]:
    """
    Convert a factor formula to Python code.
    
    Args:
        name: Factor name
        formula: Factor formula (LaTeX or Python)
        description: Factor description
        variables: Variable definitions
        model: LLM model to use
    
    Returns:
        Tuple of (success, python_code, error_message)
    """
    if not is_latex_formula(formula):
        try:
            compile(formula, '<string>', 'exec')
            return True, formula, ""
        except SyntaxError:
            pass
    
    result = convert_latex_to_python(formula, description, variables, model)
    
    if result.success:
        return True, result.python_code, ""
    else:
        return False, "", result.error or "Conversion failed"


def batch_convert_factors(
    factors: list,
    model: str = "gpt-4o-mini"
) -> Tuple[list, list]:
    """
    Batch convert factors with LaTeX formulas.
    
    Args:
        factors: List of factor dicts with 'name', 'formula', 'description', 'variables'
        model: LLM model to use
    
    Returns:
        Tuple of (converted_factors, errors)
    """
    converted = []
    errors = []
    
    for factor in factors:
        name = factor.get('name', 'Unknown')
        formula = factor.get('formula', '') or factor.get('formulation', '')
        description = factor.get('description', '')
        variables = factor.get('variables', {})
        
        if not is_latex_formula(formula):
            converted.append({
                **factor,
                'python_code': formula,
                'converted': False
            })
            continue
        
        success, python_code, error = convert_factor_to_code(
            name, formula, description, variables, model
        )
        
        if success:
            converted.append({
                **factor,
                'python_code': python_code,
                'converted': True
            })
            print(f"  ✓ {name}: LaTeX -> Python")
        else:
            errors.append({
                'name': name,
                'formula': formula,
                'error': error
            })
            print(f"  ✗ {name}: {error}")
    
    return converted, errors
