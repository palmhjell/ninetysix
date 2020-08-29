"""
Visualization functions for Plate objects or any generic DataFrame.
"""

import numpy as np
import pandas as pd

import holoviews as hv
hv.extension('bokeh')

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
    if isinstance(object, pd.DataFrame):
        df = object.copy()
        value_name = df.columns[-1]

        # Determine case
        lowers = [True for val in df.columns if val.lower() == val]
        caps = [True for val in df.columns if val.capitalize() == val]
        case = str.lower if lowers > caps else str.capitalize

    # Assume Plate
    else:
        try:
            df = object.df.copy()
            value_name = object.value_name
            case = object._standardize_case
        except AttributeError:
            raise ValueError(
                'Data format not recognized, only pandas.DataFrame and '\
                'ninetysix.Plate objects accepted.'
            )

    well, row, col = _get_ordered_locs(df)

    return df, (well, row, col), value_name, case


def plot_rof(
    object,
    value_name=None,
    color=None,
    layering=None,
    layering_order=None,
    cmap='CategoryN',
    ranked=True,
    groupby=None,
    layout=False,
    n_cols=2,
    height=350,
    width=450,
    rof_opts={},
):
    """Plot a retention-of-function-like curve (rank-ordered scatter).

    Parameters:
    -----------
    object: ns.Plate or pd.DataFrame object
        Must contain a DataFrame with columns labeled well, row, column,
        (case-insensitive) and the final column as the label (can be
        overwritten, see `value_name` kwarg).
    value_name: string, default None
        Which column in the data contains the y-axis data. Defaults to
        ns.Plate.value_name or pd.DataFrame.columns[-1].
    color: string, default None
        Either the column that should be used to color the data or the
        color all data points should be (e.g., 'green' or '#00FF00').
        If there is a column in the data that corresponds to the `color`
        input, it will be used first (before rgb/hex colors).
    layering: string, default None
        Which column in the data should be used to order the layering
        of the data. This kwarg is useful when you want certain points
        (e.g., control wells) to not be covered by other points. See 
        `layering_order` kwarg to control the specific ordering (and
        coloring) of the values in this column.
    layering_order: 'ascending', 'descending', or a list or dict.
        Layering of the data, from front to back, using the values in
        the column specified in `layering`. If providing a dictionary,
        keys are provided as the layering (in order) and values are the
        respective colors of each group.
    cmap: string, list, or dict, default 'CategoryN'
        How to color the groups of data found in `color`. Default of 
        'CategoryN' switches between 'Category10' and 'Category20'
        depending on the number of groups. If a different string, must
        be an acceptable cmap for holoviews. Otherwise, can be a list of
        colors (which matches the order of `layering`, if not None and
        if `layering_order` is not a dict), or the same dict as
        `layering_order`.
    ranked: bool, default True
        Whether to rank the data (as a true retention of function) or
        not (as a well-sorted scatter plot). Passing False is good to
        check signal-to-noise and edge effects in the plate.
    groupby: string or list, default None
        One or more columns in the data used to split the plot into
        multiple plots, usually a location (like plate number) or
        annotation.
    layout: bool, default False
        Whether or not to lay out all of the data (True) or keep it as
        a slider-based panel (False), if `groupby` was not None.
    n_cols: int, default 2
        Number of columns of laid-out plots if `layout` is True.
    height: int, default 350
        Height of the plot.
    width: int, default 450
        Width of the plot.
    rof_opts: dict, default empty dict
        Holoviews-specific opts to pass to the chart. See the holoviews
        docs. Overwrites the base plot opts if the same opt is passed.

    Returns:
    --------
    p: holoviews plot
    """
    # Get data and metadata
    df, locs, auto_value, case = _parse_data_obj(object)
    if value_name is not None:
        check_df_col(df, value_name, 'value_name')
    else:
        value_name = auto_value
    if color is not None:
        try:
            check_df_col(df, color, 'color')
            data_color = False
        except ValueError:
            data_color = True
        rof_opts['color'] = color
    if layering is not None:
        check_df_col(df, layering, 'layering')
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

    # Layering
    if layering is not None:
        if layering_order == 'ascending':
            df = df.sort_values(by=layering, ascending=True)
        if layering_order == 'descending':
            df = df.sort_values(by=layering, ascending=False)
        if isinstance(layering_order, list):
            df[layering] = pd.Categorical(df[layering], categories=layering_order)
            df = df.sort_values(by=layering, ascending=False)
            # Reverse ordering to line up
            cmap=list(reversed(cmap))
        if isinstance(layering_order, dict):
            df[layering] = pd.Categorical(
                df[layering],
                categories=layering_order.keys()
            )
            df = df.sort_values(by=layering, ascending=False)
            # Reverse ordering to line up with layering
            cmap = list(reversed(list(layering_order.values())))
        if isinstance(cmap, dict):
            df[layering] = pd.Categorical(
                df[layering],
                categories=cmap.keys()
            )
            df = df.sort_values(by=layering, ascending=False)
            # Reverse ordering to line up with layering
            cmap = list(reversed(list(cmap.values())))

    vdims = [value_name] + [val for val in df.columns if val != value_name]

    # Auto-colomapping
    if cmap == 'CategoryN':
        cmap = 'Category10'
        try:
            if len(df[color].unique()) > 10:
                cmap = 'Category20'
        except KeyError:
            pass

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
    outline=None,
    exclude_major=False,
    groupby=None,
    layout=False,
    n_cols=2,
    hm_cmap='RdBu_r',
    outline_cmap='CategoryN',
    legend=True,
    height=None,
    hm_opts={},
    colorbar_opts={},
    outline_opts={},
):
    """Plot a row-by-column heatmap.

    Parameters:
    -----------
    object: ns.Plate or pd.DataFrame object
        Must contain a DataFrame with columns labeled well, row, column,
        (case-insensitive) and the final column as the label (can be
        overwritten, see `value_name` kwarg).
    value_name: string, default None
        Which column in the data contains the heatmap coloring data.
        Defaults to ns.Plate.value_name or pd.DataFrame.columns[-1].
    outline: string, default None
        Which column in the data contains groups to be outlined for easy
        visualization.
    exclude_major: bool, default False
        Whether or not to exclude the major group from the outline to
        reduce the noise in the plot (i.e., excluding the experimental
        wells and only showing the controls).
    groupby: string or list, default None
        One or more columns in the data used to split the plot into
        multiple plots, usually a location (like plate number) or
        annotation.
    layout: bool, default False
        Whether or not to lay out all of the data (True) or keep it as
        a slider-based panel (False), if `groupby` was not None.
    n_cols: int, default 2
        Number of columns of laid-out plots if `layout` is True.
    hm_cmap: string or continuous colormap list, default 'RdBu_r'.
        How to assign values to colors on the heatmap. If a different
        string, must be an acceptable cmap for holoviews. Otherwise, can
        be a list of colors from a continuous colormap.
    outline_cmap: string, list, or dict, default 'CategoryN'
        How to color the groups of data found in `outline`. Default of 
        'CategoryN' switches between 'Category10' and 'Category20'
        depending on the number of groups. If a different string, must
        be an acceptable cmap for holoviews. Otherwise, can be a list of
        colors. If providing a dictionary, keys are provided as the
        groups (in order) and values are the respective colors of each
        group.
    legend: bool, default False
        Whether to show the outline legend.
    height: int, default None
        Height of the chart. Defaults to each row having a height of 50.
        Width is then determined automatically to keep wells square. If
        non-square wells are needed, width can be overwritten in
        `hm_opts` kwarg.
    hm_opts: dict, default empty dict
        Holoviews-specific opts to pass to the heatmap. See the
        holoviews docs. Overwrites the base opts if the same opt is
        passed.
    colorbar_opts: dict, default empty dict
        Holoviews-specific opts to pass to the heatmap's colorbar. See
        the holoviews docs. Overwrites the base opts if the same opt is
        passed.
    outline_opts: dict, default empty dict
        Holoviews-specific opts to pass to the outline chart. See the
        holoviews docs. Overwrites the base opts if the same opt is
        passed.
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
    undims = (value_name, *kdims)
    vdims = [value_name] + [val for val in df.columns if val not in undims]

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
        
        if isinstance(outline_cmap, dict):
            df_outline[outline] = pd.Categorical(
                df_outline[outline],
                categories=outline_cmap.keys()
            )
            df_outline = df_outline.sort_values(by=outline)
            # Reverse ordering to line up with order
            outline_cmap = list(outline_cmap.values())

        # Set up size of the outline boxes
        box_size = height // n_rows - (height // n_rows)*0.07

        boxes_opts = dict(
            color=outline,
            cmap=outline_cmap,
            show_legend=legend,
            marker='square',
            size=box_size,
            line_width=0.08*box_size,
            fill_alpha=0,
            legend_position='top',
            **outline_opts,
        )
        
        box_vdims = [val for val in (outline, *groupby) if val is not None]
        boxes = hv.Points(
            df_outline,
            kdims,
            box_vdims
        )
        
        if groupby != [None]:
            boxes = boxes.groupby(groupby)
            
        boxes = boxes.opts(**boxes_opts)

        p = p*boxes

        if layout and grouped != [None]:
            p = p.layout().cols(n_cols)

    return p
    

