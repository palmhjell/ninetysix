"""
Visualization functions for Plate objects or any generic DataFrame.
"""

import numpy as np
import pandas as pd

import holoviews as hv
hv.extension('bokeh')

from .plate import Plate
from .util import check_inputs, check_annotations, check_df_col


def _get_ordered_locs(df):
    """Returns location information in 'well', 'row', 'column' order."""
    well = [val for val in df.columns if val.lower() == 'well']
    row = [val for val in df.columns if val.lower() == 'row']
    column = [val for val in df.columns if val.lower() == 'column']

    for loc in (well, row, column):
        if not loc:
            raise ValueError(
                f'Could not find column for "{loc}"'
            )
        if len(loc) > 1:
            raise ValueError(
                f'Too many columns found: "{loc}"'
            )
    
    return well[0], row[0], column[0]


def _parse_data_obj(object):
    """Gets necessary information for 96-well-based plots"""
    if isinstance(object, Plate):
        df = object.df.copy()
        value_name = object.value_name
        case = object._standardize_case

    elif isinstance(object, pd.DataFrame):
        df = object.copy()
        value_name = df.columns[-1]

        # Determine case
        lowers = [True for val in df.columns if val.lower() == val]
        caps = [True for val in df.columns if val.capitalize() == val]
        case = str.lower if lowers > caps else str.capitalize

    well, row, col = _get_ordered_locs(df)

    return df, (well, row, col), value_name, case


def plot_rof(
    object,
    value_name=None,
    color=None,
    sort=None,
    sort_order=None,
    groupby=None,
    layout=False,
    n_cols=2,
    cmap='CategoryN',
    ranked=True,
    height=350,
    width=450,
    rof_opts={},
):
    """Plot retention of function curve, a rank-ordered scatter plot.
    
    """
    # Get data and metadata
    df, locs, auto_value, case = _parse_data_obj(object)
    if value_name is not None:
        check_df_col(df, value_name, 'value_name')
    else:
        value_name = auto_value
    if color is not None:
        check_df_col(df, color, 'color')
        rof_opts['color'] = color
    if sort is not None:
        check_df_col(df, sort, 'sort')
    if not isinstance(groupby, list):
        groupby = [groupby]
    if groupby != [None]:
        for group in groupby:
            check_df_col(df, group, 'groupby')

    if ranked:
        xaxis = 'bottom'
        if case('rank') not in df.columns:
            if groupby == [None]:
                df[case('rank')] = df[value_name].rank(ascending=False)
            else:
                grouped = df.groupby(groupby)[value_name]
                df[case('rank')] = grouped.rank(ascending=False)
        df = df.sort_values(by=case('rank'), ascending=True)
        kdims = case('rank')
    else:
        # Order by well
        kdims = locs[0]
        df = df.sort_values(by=locs[0], ascending=True)
        xaxis = 'bare'

    # Sort
    if sort is not None:
        if sort_order == 'ascending':
            df = df.sort_values(by=sort, ascending=True)
        if sort_order == 'descending':
            df = df.sort_values(by=sort, ascending=False)
        if isinstance(sort_order, list):
            df[sort] = pd.Categorical(df[sort], categories=sort_order)
            df = df.sort_values(by=sort, ascending=False)
            # Reverse ordering to line up
            cmap=list(reversed(cmap))
        if isinstance(sort_order, dict):
            df[sort] = pd.Categorical(df[sort], categories=sort_order.keys())
            df = df.sort_values(by=sort, ascending=False)
            # Reverse ordering to line up
            cmap = list(reversed(list(sort_order.values())))

    vdims = [val for val in (value_name, color, *groupby) if val is not None]

    # Auto-colomapping
    if cmap == 'CategoryN':
        if len(df[color].unique()) <= 10:
            cmap = 'Category10'
        else:
            cmap = 'Category20'

    # Set up options; entries can be overwritten by rof_opts
    base_opts = dict(
        height=height,
        width=width,
        xaxis=xaxis,
        size=10,
        fill_alpha=1,
        alpha=0.75,
        cmap=cmap,
        fontsize=dict(title=9),
        line_width=2,
        line_color='black',
        padding=0.05,
        toolbar='above',
        tools=['hover'],
        **rof_opts,
    )

    p = hv.Scatter(
        df,
        kdims,
        vdims
    )
    
    if groupby != [None]:
        p = p.groupby(groupby)
    
    p = p.opts(**base_opts)

    if layout and grouped != [None]:
        p = p.layout().cols(n_cols)

    return p


def plot_hm(
    object,
    value_name=None,
    height=None,
    outline=None,
    exclude_major=False,
    groupby=None,
    layout=False,
    n_cols=2,
    hm_cmap='RdBu_r',
    outline_cmap='CategoryN',
    legend=True,
    hm_opts={},
    colorbar_opts={},
    outline_opts={},
):
    """Plot a heatmap.
    
    """
    # Get data and metadata
    df, locs, auto_value, case = _parse_data_obj(object)
    if value_name is not None:
        check_df_col(df, value_name, 'value_name')
    else:
        value_name = auto_value
    if outline is not None:
        check_df_col(df, outline, 'outline')
    if not isinstance(groupby, list):
        groupby = [groupby]
    if groupby != [None]:
        for group in groupby:
            check_df_col(df, group, 'groupby')

    # Non-int column
    df[locs[2]] = df[locs[2]].astype(str)

    kdims = [locs[2], locs[1]]
    vdims = [val for val in (value_name, outline, *groupby) if val is not None]

    # Adjust heights
    n_rows = len(df[locs[1]].unique())
    n_cols = len(df[locs[2]].unique())
    if height is None:
        height = int(50 * n_rows)
    width = height * n_cols // n_rows

    # Set the plot options; can be overwritten
    base_opts = dict(
        cmap=hm_cmap,
        xaxis='top',
        frame_height=height,
        frame_width=width,
        colorbar=True,
        invert_yaxis=True,
        tools=['hover'],
        **hm_opts,
    )

    base_colorbar_opts = dict(
        title=value_name,
        title_text_align='left',
        height=int(0.9*height),
        padding=40,
        location=(-30, -20),
        bar_line_color=None,
        major_tick_line_color=None,
        label_standoff=5,
        background_fill_color=None,
        **colorbar_opts,
    )

    base_opts['colorbar_opts'] = base_colorbar_opts

    # Make the plot
    p = hv.HeatMap(
        df,
        kdims,
        vdims
    )
    
    if groupby != [None]:
        p = p.groupby(groupby)
        
    p = p.opts(**base_opts)

    # Add outlines
    if outline is not None:
        if exclude_major:
            major = df[outline].value_counts().index[0]
            df_outline = df[df[outline] != major].copy()
        else:
            df_outline = df.copy()

        # Need string for legend to show; categorical stuff
        df_outline[outline] = df_outline[outline].astype(str)

        # Auto-colomapping
        if outline_cmap == 'CategoryN':
            if len(df_outline[outline].unique()) <= 10:
                outline_cmap = 'Category10'
            else:
                outline_cmap = 'Category20'

        boxes_opts = dict(
            color=outline,
            cmap=outline_cmap,
            show_legend=legend,
            marker='square',
            size=height // n_rows - (height // n_rows)*0.07,
            line_width=0.01*height,
            fill_alpha=0,
            legend_position='top',
            **outline_opts,
        )
        
        boxes = hv.Points(
            df_outline,
            kdims,
            [outline, *vdims]
        )
        
        if groupby != [None]:
            boxes = boxes.groupby(groupby)
            
        boxes = boxes.opts(**boxes_opts)

        p = p*boxes

        if layout and grouped != [None]:
            p = p.layout().cols(n_cols)

    return p
    

