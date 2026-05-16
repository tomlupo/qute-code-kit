"""
VectorBT Backtesting Wrapper Module

This module provides a wrapper around VectorBT for backtesting portfolio strategies with
various rebalancing methods, including:
1. Periodic rebalancing (daily, weekly, monthly, etc.)
2. Rebalancing bands (absolute and relative deviation thresholds)
3. Combination of periodic rebalancing and rebalancing bands

Note that all tickers are assumed to represent prices in the same currency.

The module implements two main functions:
- run_backtest: For standard periodic rebalancing
- run_backtest_with_bands: For rebalancing bands with optional periodic rebalancing

Example usage:
```python
# Run a backtest with no rebalancing (buy and hold)
pf = run_backtest(prices, weights, rebalancing_freq=None)

# Run a backtest with monthly rebalancing
pf = run_backtest(prices, weights, rebalancing_freq="1M")

# Run a backtest with absolute threshold rebalancing (5%)
pf = run_backtest_with_bands(prices, weights, abs_threshold=5, rel_threshold=0)

# Run a backtest with relative threshold rebalancing (25%)
pf = run_backtest_with_bands(prices, weights, abs_threshold=0, rel_threshold=25)

# Run a backtest with both absolute and relative threshold rebalancing
pf = run_backtest_with_bands(prices, weights, abs_threshold=5, rel_threshold=25)

# Run a backtest with monthly rebalancing and rebalancing bands
pf = run_backtest_with_bands(prices, weights, abs_threshold=5, rel_threshold=25, rebalancing_freq="1M")
```
"""

import vectorbt as vbt
import pandas as pd
import numpy as np
import warnings
import os
from numba import njit
from vectorbt.portfolio.nb import order_nb, sort_call_seq_nb, sort_call_seq_out_nb, get_group_value_ctx_nb, insert_argsort_nb, approx_order_value_nb, get_col_elem_nb, get_elem_nb,flex_select_auto_nb, order_nothing_nb
from vectorbt.portfolio.enums import SizeType, Direction, NoOrder, Order
import numba as nb

# %% settings
num_tests = 10
vbt.settings.array_wrapper['freq'] = 'days'
vbt.settings.returns['year_freq'] = '252 days'
vbt.settings.portfolio['seed'] = 42
vbt.settings.portfolio.stats['incl_unrealized'] = True


# %% helpers
def get_rebalancing_dates(dates: pd.DatetimeIndex, rebalancing_freq) -> pd.DatetimeIndex:
    """
    Determine the rebalancing dates according to the rebalancing frequency.

    Args:
        dates (pd.DatetimeIndex): Datetime index representing the dates of the data.
        rebalancing_freq: Frequency at which the portfolio should be rebalanced. 
                          Can be None, an integer, a string ('D', 'W', 'M', 'Y'), or a list of dates.

    Returns:
        pd.DatetimeIndex: The actual rebalancing dates.

    Raises:
        ValueError: If the rebalancing frequency is invalid.
    """
    dates = pd.DatetimeIndex(dates)
    rebalancing_dates = pd.DatetimeIndex([])

    if rebalancing_freq is None:
        # No rebalancing, buy and hold
        rebalancing_dates = pd.DatetimeIndex([dates[0]])  # Only first date
    elif isinstance(rebalancing_freq, int):
        # Rebalance every nth date
        rebalancing_dates = dates[::rebalancing_freq]
    elif isinstance(rebalancing_freq, str):
        # Use pandas date offset
        if rebalancing_freq[-1].isalpha():
            unit = rebalancing_freq[-1].lower()
            value = int(rebalancing_freq[:-1]) if rebalancing_freq[:-1].isdigit() else 1
            unit_mapping = {'d': 'days', 'w': 'weeks', 'm': 'months', 'y': 'years'}
            offset = pd.DateOffset(**{unit_mapping[unit]: value})
            rebalancing_dates = pd.date_range(start=dates[0], end=dates[-1], freq=offset)
        else:
            raise ValueError('Invalid rebalancing frequency format.')
    elif isinstance(rebalancing_freq, list):
        # Rebalance on given dates
        rebalancing_dates = pd.DatetimeIndex(rebalancing_freq)
    else:
        raise ValueError('Invalid rebalancing frequency type.')

    return rebalancing_dates

# %% main function
def run(prices: pd.DataFrame, 
        weights: dict, 
        rebalancing_freq=1, 
        threshold=None,        
        fees=0.0,
        fixed_fees=0.0,
        slippage=0.0,
        use_order_func=None, 
        use_numba=True) -> vbt.Portfolio:
    """
    Run a backtest using the provided prices, weights, and rebalancing frequency.

    Args:
        prices (pd.DataFrame): Asset price data indexed by date.
        weights (dict): Dictionary of strategy names to weight DataFrames.
        rebalancing_freq: Frequency at which the portfolio should be rebalanced. 
                          Can be None, an integer, a string ('D', 'W', 'M', 'Y'), or a list of dates.
        threshold (float, optional): Threshold for deviation that triggers rebalancing. Defaults to None.
        fees (float, optional): Fee rate for transactions. Defaults to None.
        fixed_fees (float, optional): Fixed fee for transactions. Defaults to None.
        slippage (float, optional): Slippage rate for transactions. Defaults to None.
        use_order_func (bool, optional): Whether to use the order function. Defaults to None.
        use_numba (bool, optional): Whether to use Numba. Defaults to True.

    Returns:
        vbt.Portfolio: The resulting portfolio from the backtest.

    Raises:
        ValueError: If the weights DataFrame is not properly aligned with the prices DataFrame.
    """
    
    # Validate inputs
    if not isinstance(prices, pd.DataFrame):
        raise ValueError('prices must be a pandas DataFrame')
    if not isinstance(weights, dict):
        raise ValueError('weights must be a dictionary')
    if not isinstance(rebalancing_freq, (type(None), int, str, list)):
        raise ValueError('rebalancing_freq must be None, an integer, a string, or a list')
    if not set().union(*[v.columns for v in weights.values()]).issubset(prices.columns):
        raise ValueError('All tickers in weights must be present in prices')

    # Define low level functions
    def pre_sim_func_nb(c, rebalancing_mask):
        """
        Pre-simulation function that sets up the rebalancing mask.
        
        Args:
            c: Simulation context object.
            rebalancing_mask: Boolean array indicating rebalancing dates.
            
        Returns:
            Empty tuple.
        """
        # Define rebalancing days
        c.segment_mask[:, :] = False
        c.segment_mask[rebalancing_mask, :] = True
        return ()

    def pre_group_func_nb(c):
        #print('\tbefore group', c.group)
        return ()

    def pre_segment_func_nb(c, size, size_type, direction, threshold):
        """
        Pre-segment function that determines if rebalancing is needed based on deviation from target weights.
        
        Args:
            c: Simulation context object.
            size: Array of target weights.
            size_type: Size type for orders.
            direction: Direction for orders.
            threshold: Threshold for deviation that triggers rebalancing (as float).
            
        Returns:
            Tuple containing target weights if rebalancing is needed, or None if not.
        """
        # Allocate an array for position values.
        position_values = np.empty(c.group_len, dtype=np.float64)
        # Loop over each column in the current group.
        for i, col in enumerate(range(c.from_col, c.to_col)):
            # Update the last valuation price for the column.
            c.last_val_price[col] = get_col_elem_nb(c, col, c.close)
            # Calculate position value.
            position_values[i] = c.last_val_price[col] * c.last_position[col]
        
        # Compute the total value once.
        total_value = np.sum(position_values) + c.last_free_cash[c.group]
        # Compute the current weights.
        position_weights = position_values / total_value

        # Check if deviation is greater than threshold
        target_weights = size[c.i, c.from_col:c.to_col]
        deviation = np.abs(position_weights - target_weights)
        
        # Replace built-in 'any' with a Numba-compatible loop
        rebalancing_flag = False
        for dev in deviation:
            if dev > threshold:  # threshold is now guaranteed to be a float
                rebalancing_flag = True
                break

        if rebalancing_flag:
            # Reorder call sequence of this segment such that selling orders come first and buying last
            # Rearranges c.call_seq_now based on order value (size, size_type, direction, and val_price)
            order_value_out = np.empty(c.group_len, dtype=np.float64)
            sort_call_seq_nb(c, size, size_type=size_type, direction=direction, order_value_out=order_value_out)
            return (target_weights,)
        else:
            return (None,)

    def order_func_nb(c, weights, size_type, direction, fees, fixed_fees, slippage):
        #print('\t\t\tcreating order', c.call_idx, 'at column', c.col)
        if weights is None:
            return order_nothing_nb()
        # Create and return an order
        col_i = c.call_seq_now[c.call_idx]
        return order_nb(
            size=weights[col_i],
            price=get_elem_nb(c, c.close),
            size_type=np.int64(get_elem_nb(c, size_type)),
            direction=np.int64(get_elem_nb(c, direction)),
            fees=np.float64(get_elem_nb(c, fees)),
            fixed_fees=np.float64(get_elem_nb(c, fixed_fees)),
            slippage=np.float64(get_elem_nb(c, slippage)),
            log=True
        )

    def post_order_func_nb(c, weights):
        #print('\t\t\t\torder status:', c.order_result.status)
        return None

    # Set use_order_func
    if threshold is not None:
        if use_order_func is False:
            warnings.warn('use_order_func is set to False, but threshold is not None. Changing use_order_func to True.')
        use_order_func = True
    else:
        if use_order_func is None:
            use_order_func = False
        # Set a default threshold value for Numba compatibility if using order_func
        if use_order_func:
            threshold = 0.0  # Default to 0.0 to ensure it's a float for Numba

    # Set numba
    if use_numba:
        os.environ['NUMBA_DISABLE_JIT'] = '0'
        pre_sim_func_nb = njit(pre_sim_func_nb)
        pre_group_func_nb = njit(pre_group_func_nb)
        pre_segment_func_nb = njit(pre_segment_func_nb)
        order_func_nb = njit(order_func_nb)
        post_order_func_nb = njit(post_order_func_nb)
    else:
        os.environ['NUMBA_DISABLE_JIT'] = '1'

    # Convert weights to vbt format
    weights_df = pd.concat(weights, axis=1, names=['strategy'])

    # Allign prices and weights indices
    index = prices.index.union(weights_df.index)
    prices = prices.reindex(index).ffill()
    weights_df = weights_df.reindex(index).ffill()

    # Convert indices to DatetimeIndex
    index = pd.to_datetime(index)
    prices.index = pd.to_datetime(prices.index)
    weights_df.index = pd.to_datetime(weights_df.index)

    # Get rebalancing dates
    rebalancing_dates = get_rebalancing_dates(index, rebalancing_freq)

    # Create prices DataFrame with same structure as weights_df
    _prices = prices[weights_df.columns.get_level_values(1)]
    _prices.columns = weights_df.columns

    # Set order func arguments
    size_type = np.asarray(SizeType.TargetPercent)
    direction = np.asarray(Direction.LongOnly)
    fees = np.asarray(fees)
    fixed_fees = np.asarray(fixed_fees)
    slippage = np.asarray(slippage)

    if use_order_func:
        # Create rebalancing mask
        rebalancing_mask = index.isin(rebalancing_dates)
        
        # Convert weights to numpy array for use in simulation
        size_arr = weights_df.values

        # Ensure threshold is a float for Numba compatibility
        threshold = float(threshold)

        # Run simulation with custom order function for rebalancing bands
        pf =  vbt.Portfolio.from_order_func(
            _prices,
            order_func_nb,
            size_type, 
            direction, 
            fees, 
            fixed_fees, 
            slippage,
            pre_sim_func_nb=pre_sim_func_nb,
            pre_sim_args=(rebalancing_mask,),
            pre_group_func_nb=pre_group_func_nb,
            pre_segment_func_nb=pre_segment_func_nb,
            pre_segment_args=(size_arr, size_type, direction, threshold),
            post_order_func_nb=post_order_func_nb,
            group_by='strategy',
            cash_sharing=True,
            use_numba=use_numba
        )
        
        return pf

    else:
        # Create size DataFrame
        size = weights_df.copy()
        size.loc[~size.index.isin(rebalancing_dates), :] = None

        # Run simulation
        pf = vbt.Portfolio.from_orders(
            close=_prices,
            size=size,
            size_type=size_type,
            direction=direction,
            group_by='strategy',
            cash_sharing=True,
            call_seq='auto',  # Ensure proper rebalancing order (sell before buy)
            fees=fees,
            fixed_fees=fixed_fees,
            slippage=slippage
        )

        return pf