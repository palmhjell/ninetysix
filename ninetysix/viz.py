"""
Visualization functions for Plate objects or any generic DataFrame.
"""

import numpy as np
import pandas as pd

import holoviews as hv
hv.extension('bokeh')
import bokeh.palettes

from .util import check_df_col

class Colors():
    """Mild color palette."""
    blue = '#3E94FA'
    green = '#8DED81'
    orange = '#E18409'
    gray = '#DEDEDE'


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


def _parse_data_obj(obj):
    """Gets necessary information for 96-well-based plots"""
    if isinstance(obj, pd.DataFrame):
        df = obj.copy()
        value_name = df.columns[-1]

        # Determine case
        lowers = [True for val in df.columns if val.lower() == val]
        caps = [True for val in df.columns if val.capitalize() == val]
        case = str.lower if lowers > caps else str.capitalize

    # Assume Plate
    else:
        try:
            df = obj.df.copy()
            value_name = obj.value_name
            case = obj._set_case
        except AttributeError:
            raise ValueError(
                'Data format not recognized, only pandas.DataFrame and '\
                'ninetysix.Plate objects accepted.'
            )

    # Get well, row, and column values
    try:
        well, row, col = _get_ordered_locs(df)
        locs = (well, row, col)
    except ValueError:
        locs = None

    return df, locs, value_name, case


def _center_colormap(data, cmap_center):
    """Stretch a color map so that its center is at `cmap_center`."""
    if not isinstance(cmap_center, (float, int)):
        raise TypeError(
            'cmap_center argument must be float or int.'
        )
    if not min(data) < cmap_center < max(data):
        raise ValueError('Must have min(data) < cmap_center < max(data).')

    dist = max(max(data) - cmap_center, cmap_center - min(data))
    dist += dist / 100

    return list(np.linspace(cmap_center-dist, cmap_center+dist, 257))


def aggregate_replicates(df, variable, value, grouping):
    """Checks for the presence of replicates in the values of a dataset,
    given some experimental conditions. Returns True if the standard
    deviation of the values of each group (if more than one exists) is
    greater than 0, indicating that replicates were performed under the
    given criteria.
    
    Parameters:
    -----------
    df: pandas DataFrame in tidy format
        The dataset to be checked for replicates.
    variable: string
        Name of column of data frame for the independent variable,
        indicating a specific experimental condition.
    value: string
        Name of column of data frame for the dependent variable,
        indicating an experimental observation.
    grouping: list of strings
        Column name or list of column names that indicates how the
        data set should be split.
    
    Returns:
    --------
    replicates: bool
        True if replicates are present.
    df_agg: pd.DataFrame
        The DataFrame containing averaged 'variable' values, if
        replicates is True. Otherwise returns the original DataFrame.
        The aggregated data is in a new column
    """
    # Unpack the experimental conditions into a single list of arguments
    if not isinstance(grouping, (list, tuple)):
        grouping = [grouping]
    args = [elem for elem in (variable, *grouping) if elem is not None]

    # Get stdev of argument groups
    grouped = df.groupby(args)[value]
    group_stdevs = grouped.std().reset_index()
    group_stdev = group_stdevs[value].mean()

    # Determine if there are replicates (mean > 0)
    replicates = bool(group_stdev > 0)

    # Average the values and return
    if replicates:
        df_mean = grouped.mean().reset_index()
        df_mean.columns = list(df_mean.columns[:-1]) + ['mean_' + str(value)]
        df = df.merge(df_mean)

    return replicates, df


def plot_scatter(
    obj,
    variable=None,
    value_name=None,
    color=None,
    layering=None,
    layering_order=None,
    cmap='CategoryN',
    ranked=False,
    groupby=None,
    layout=False,
    n_cols=2,
    height=350,
    width=450,
    plot_opts=None,
):
    """Create a well-activity scatter plot.

    Parameters:
    -----------
    obj: ns.Plate or pd.DataFrame objectect
        Must contain a DataFrame with columns labeled well, row, column,
        (case-insensitive) and the final column as the value (can be
        overwritten, see `value_name` kwarg).
    variable: string, default None
        If None, `obj` must contain a well column. Otherwise specifies
        the variable on the x-axis of the scatter chart.
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
    ranked: bool, default False
        Whether to rank the data (as a retention-of-function-like curve)
        or not (as a well-sorted scatter plot). Passing False is good to
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
    plot_opts: dict, default None
        Holoviews-specific opts to pass to the chart. See the holoviews
        docs. Overwrites the base plot opts if the same opt is passed.

    Returns:
    --------
    p: Holoviews plot
    """
    if plot_opts is None:
        plot_opts = {}
    # Get data and metadata
    df, locs, auto_value, case = _parse_data_obj(obj)
    if value_name is not None:
        check_df_col(df, value_name, 'value_name')
    else:
        value_name = auto_value
    
    try:
        check_df_col(df, color, 'color')
    except ValueError:
        # Assuming color is not column name but actual color; test
        try:
            hv.Scatter(df).opts(color=color)
        except ValueError:
            raise ValueError(
                f'Unusable color kwarg. {color} not an acceptable option.'
            )

    if color is not None:
        plot_opts['color'] = color
    
    check_df_col(df, variable, 'variable')
    check_df_col(df, layering, 'layering')
    
    if not isinstance(groupby, list):
        groupby = [groupby]
    for group in groupby:
        check_df_col(df, group, 'groupby')

    if case('rank') not in df.columns:
        if groupby == [None]:
            df[case('rank')] = df[value_name].rank(ascending=False, method='first')
        else:
            grouped = df.groupby(groupby)[value_name]
            df[case('rank')] = grouped.rank(ascending=False, method='first')
    
    secondary_sort = []
    kdims = []
    if ranked:
        secondary_sort.append(case('rank'))
        kdims.append(case('rank'))
    elif variable is None:
        if locs is None:
            raise ValueError(
                'Data object does not contain column related to well. This is '
                'required if a variable is not specified and ranked is False.'
            )
        plot_opts['xticks'] = 0
        # Order by well (A1-H12 ordering)
        secondary_sort += [locs[1], locs[2]]
        # kdims = well
        kdims = locs[0]
    else:
        kdims = variable
        secondary_sort.append(variable)


    
    df = df.sort_values(by=secondary_sort, ascending=True)

    # Layering
    if layering is not None:
        if layering_order == 'ascending':
            df = df.sort_values(by=[layering, *secondary_sort], ascending=True)
        if layering_order == 'descending':
            df = df.sort_values(by=[layering, *secondary_sort], ascending=False)
        if isinstance(layering_order, list):
            df[layering] = pd.Categorical(df[layering], categories=layering_order)
            # Reverse ordering to line up
            cmap=list(reversed(cmap))
        if isinstance(layering_order, dict):
            df[layering] = pd.Categorical(
                df[layering],
                categories=layering_order.keys()
            )
            # Reverse ordering to line up with layering
            cmap = list(reversed(list(layering_order.values())))
        if isinstance(cmap, dict):
            df[layering] = pd.Categorical(
                df[layering],
                categories=cmap.keys()
            )
            # Reverse ordering to line up with layering
            cmap = list(reversed(list(cmap.values())))

        df = df.sort_values(by=[layering, *secondary_sort], ascending=not ranked)

    elif color is not None:
        if isinstance(cmap, dict):
            df[color] = pd.Categorical(
                df[color],
                categories=cmap.keys()
            )
            # Reverse ordering to line up with layering
            if ranked:
                cmap = list(reversed(list(cmap.values())))
            else:
                cmap = list(cmap.values())

            df = df.sort_values(by=[color, *secondary_sort], ascending=not ranked)

    vdims = [value_name] + [val for val in df.columns if val != value_name]

    # Auto-colomapping
    if cmap == 'CategoryN':
        cmap = 'Category10'
        try:
            if len(df[color].unique()) > 10:
                cmap = 'Category20'
        except KeyError:
            pass

    # Set up options; entries can be overwritten by plot_opts
    base_opts = dict(
        height=height,
        width=width,
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
        **plot_opts,
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


def plot_rof(*args, **kwargs):
    """Create a retention of function curve, or a rank-ordered scatter
    plot. See `plot_scatter` for more details.

    Parameters:
    -----------
    object: ns.Plate or pd.DataFrame objectect
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
        Whether to rank the data (as a retention-of-function-like curve)
        or not (as a well-sorted scatter plot). Passing False is good to
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
    plot_opts: dict, default None
        Holoviews-specific opts to pass to the chart. See the holoviews
        docs. Overwrites the base plot opts if the same opt is passed.

    Returns:
    --------
    p: Holoviews plot
    """
    if 'ranked' not in kwargs:
        kwargs['ranked'] = True
    return plot_scatter(*args, **kwargs)


def plot_hm(
    obj,
    value_name=None,
    outline=None,
    exclude_major=False,
    groupby=None,
    layout=False,
    n_cols=2,
    hm_cmap='RdBu_r',
    cmap_center=None,
    outline_cmap='CategoryN',
    legend=True,
    height=None,
    hm_opts=None,
    colorbar_opts=None,
    outline_opts=None,
):
    """Plot a row-by-column heatmap.

    Parameters:
    -----------
    obj: ns.Plate or pd.DataFrame object
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
    cmap_center: float or int, default None
        The center of the heatmap's colormap. Useful for setting the
        center of a diverging colormap to an important value (like a
        control).
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
    hm_opts: dict, default None
        Holoviews-specific opts to pass to the heatmap. See the
        holoviews docs. Overwrites the base opts if the same opt is
        passed.
    colorbar_opts: dict, default None
        Holoviews-specific opts to pass to the heatmap's colorbar. See
        the holoviews docs. Overwrites the base opts if the same opt is
        passed.
    outline_opts: dict, default None
        Holoviews-specific opts to pass to the outline chart. See the
        holoviews docs. Overwrites the base opts if the same opt is
        passed.

    Returns:
    --------
    p: Holoviews plot
    """
    if hm_opts is None:
        hm_opts = {}
    if colorbar_opts is None:
        colorbar_opts = {}
    if outline_opts is None:
        outline_opts = {}
    # Get data and metadata
    df, locs, auto_value, case = _parse_data_obj(obj)
    if locs is None:
        raise ValueError(
            'DataFrame is missing well, row, and/or column information. '
            'This is necessary for this visualization.'
        )
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
    hm_rows = len(df[locs[1]].unique())
    hm_cols = len(df[locs[2]].unique())
    if height is None:
        height = int(50 * hm_rows)
    width = height * hm_cols // hm_rows

    # Center colorbar
    if cmap_center is None:
        # Default to middle of data range (normal behavior)
        values = df[value_name]
        cmap_center = min(values) + (max(values) - min(values))/2

    color_levels = _center_colormap(df[value_name].dropna(), cmap_center)

    # Set the plot options; can be overwritten
    base_opts = dict(
        cmap=hm_cmap,
        xaxis='top',
        frame_height=height,
        frame_width=width,
        colorbar=True,
        color_levels=color_levels,
        invert_yaxis=True,
        tools=['hover'],
        line_width=2,
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
    major = None
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
            # Remove major from dictionary if it exists
            outline_cmap = outline_cmap.copy()
            outline_cmap.pop(major, None)

            df_outline[outline] = pd.Categorical(
                df_outline[outline],
                categories=outline_cmap.keys()
            )
            df_outline = df_outline.sort_values(by=outline)
            # Reverse ordering to line up with order
            outline_cmap = list(outline_cmap.values())

        # Set up size of the outline boxes
        box_size = height // hm_rows - (height // hm_rows)*0.07

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

        if layout and groupby != [None]:
            p = p.layout().cols(n_cols)

    return p


def plot_bar(
    obj,
    variable,
    value_name=None,
    groupby=None,
    color=None,
    sort=None,
    cmap='CategoryN',
    show_points=True,
    layout=False,
    n_cols=2,
    legend=False,
    xrotation=0,
    jitter=0,
    height=350,
    width=300,
):
    """Converts a tidy DataFrame a bar plot, taking care to show all
    the data. Bars are given as the average of each grouping of the
    variable (which can be further split by the split argument), and
    the actual data points are overlaid on top.
    
    Parameters:
    -----------
    obj: ns.Plate or pd.DataFrame object
        If DataFrame and `value = None`, the final column is used as the
        value.
    variable: str
        Column in DataFrame representing the variable, plotted on
        the x-axis.
    value_name: str, default None
        Column in DataFrame/Plate representing the quantitative value,
        plotted on the y-axis.
    groupby: str, default None
        The names of one or more columns that further specify the
        way the data is grouped.
    sort: str, default NNone.
        Which column is used to determine the sorting of the data.
        Defaults to None, and will sort by the condition column
        (alphabetical) if present, otherwise variable.
    cmap: str, default 'CategoryN'
        The colormap to use. Any Holoviews/Bokeh colormap is fine.
        Defaults to Category10 or Category20 depending on number of
        unique plot elements.
    show_points: bool, default True
        Shows all the data points. I don't even know why this is an
        argument. Default will show points if there are multiple
        replicates. Unless you have a really good reason, don't
        change this.
    layout: bool, default False
        Whether or not to lay out all of the data (True) or keep it as
        a slider-based panel (False), if `groupby` was not None.
    n_cols: int, default 2
        Number of columns of laid-out plots if `layout` is True.
    legend: bool/str, default False
        First controls whether or not the legend is shown, then its
        position. Defaults to False, though 'top' would be a good
        option, or 'top_left' if using split.
    xrotation: int, default 0
        Rotation of the x-labels in degrees.
    height: int, default 350
        The height of the chart.
    width: int, default 300
        The width of the chart.

    Returns:
    --------
    chart: Holoviews chart
    """
    # Get data and metadata
    df, locs, auto_value, case = _parse_data_obj(obj)
    if value_name is not None:
        check_df_col(df, value_name, 'value_name')
    else:
        value_name = auto_value
    
    # Check columns
    check_df_col(df, variable, 'variable')
    check_df_col(df, color, 'color')
    check_df_col(df, sort, 'sort')

    if not isinstance(groupby, (list, tuple)):
        groupby = [groupby]
    for group in groupby:
        check_df_col(df, group, 'groupby')

    # Auto-colomapping
    if cmap == 'CategoryN':
        if len(df[variable].unique()) <= 10:
            cmap = 'Category10'
        else:
            cmap = 'Category20'
    
    replicates, df = aggregate_replicates(df, variable, value_name, groupby)

    # Sort
    if sort is not None:
        check_df_col(df, sort, name='sort')
        df = df.sort_values(by=sort).reset_index(drop=True)
    
    # Check jitter value
    if not isinstance(jitter, (float, int)) or isinstance(jitter, bool):
        raise ValueError('Jitter must be an explicit numeric value.')
    if jitter > 1:
        # Paternalism (shout out to seaborn)
        raise ValueError('No. Jitter > 1 is misleading.')

    # Encode color
    if color is None:
        color = variable

    # If color is the value column, make it the mean
    if color == value_name:
        color = f'mean_{value_name}'

    # Pull out available encodings (column names)
    encodings = [*list(df.columns)]

    # Make bar chart
    bars = hv.Bars(
        df,
        variable,
        [(f'mean_{value_name}', value_name), *encodings],
    )

    # Determine single-point entries
    args = [elem for elem in [variable] + groupby if elem is not None]
    counts = (df.groupby(args).count() ==
                1).reset_index()[[variable, value_name]]
    counts.columns = [variable, 'counts']

    # Get list of singlets to drop from plotting df
    singlets = counts[counts['counts']][variable].to_list()

    # Make scatter chart
    points = hv.Scatter(
        df[~df[variable].isin(singlets)],
        variable,
        [value_name, *encodings],
    )

    # Make the split
    if groupby != [None]:
        bars = bars.groupby(groupby)
        points = points.groupby(groupby)

    # Output chart as only bars, or bars and points
    if show_points is None:
        if replicates:
            chart = bars*points
        else:
            chart = bars
    elif show_points:
        chart = bars*points
    else:
        chart = bars

    # Set options (this is probably horribly inefficient right now)
    base_opts = dict(
        height=height,
        width=width,
        ylim=(0, 1.1*np.max(df[value_name])),
        xrotation=xrotation,
        color=color,
        cmap=cmap,
        show_legend=legend,
    )

    bar_opts = base_opts
    scat_opts = dict(
        size=6,
        fill_alpha=0.2,
        color='black',
        jitter=jitter,
    )

    # Add to chart
    chart.opts({
        'Bars': bar_opts,
        'Scatter': scat_opts,
    })

    if layout and groupby != [None]:
        chart = chart.layout().cols(n_cols)

    return chart


def plot_curve(
    obj,
    variable,
    value_name=None,
    condition=None,
    groupby=None,
    sort=None,
    cmap='CategoryN',
    show_all=False,
    show_points=None,
    legend=False,
    height=350,
    width=500,
):
    """Converts a tidy DataFrame containing timecourse-like data
    into a plot, taking care to show all the data. A line is
    computed as the average of each set of points (grouped by the
    condition and groupby, if present), and the actual data points are 
    overlaid on top.
    
    Parameters:
    -----------
    obj: ns.Plate or pd.DataFrame object
        If DataFrame and `value = None`, the final column is used as the
        value.
    variable: str
        Column in DataFrame representing a timecourse-like variable,
        plotted on the x-axis.
    value_name: str
        Column in DataFrame representing the quantitative value,
        plotted on the y-axis.
    condition: str
        The names of one or more columns that specifies way the data
        is grouped for a single chart. Defaults to None.
    groupby:  str
        The names of one or more columns that further specify the
        way the data is grouped between different charts. Defaults
        to None.
    cmap: The colormap to use. Any Holoviews/Bokeh colormap is fine.
        Uses Holoviews default if None.
    show_all: bool
        If groupby is not None, whether or not to use a drop-down or
        to show all the plots (layout). Note that this can be pretty
        buggy from Holoview's layout system. There is usually a way
        to how all the info you want, in a nice way. Just play
        around.
    show_points: bool
        Shows all the data points. I don't even know why this is an
        argument. Default will show points if there are multiple
        replicates. Unless you have a really good reason, don't
        change this.
    legend: str
        First controls whether or not the legend is shown, then its
        position. Defaults to False, though 'top' would be a good
        option, or 'top_left' if using groupby.
    height: int
        The height of the chart.
    width: int
        The width of the chart.
    
    Returns:
    --------
    chart: the final Holoviews chart
    """
    # Get data and metadata
    df, locs, auto_value, case = _parse_data_obj(obj)
    if value_name is not None:
        check_df_col(df, value_name, 'value_name')
    else:
        value_name = auto_value
    
    # Check columns
    check_df_col(df, variable, 'variable')
    check_df_col(df, condition, 'condition')

    if not isinstance(groupby, (list, tuple)):
        groupby = [groupby]
    for group in groupby:
        check_df_col(df, group, 'groupby')

    groups = [elem for elem in (condition, *groupby) if elem is not None]
    replicates, df = aggregate_replicates(df, variable, value_name, groups)

    # Auto-colomapping
    if condition is None:
        n_conditions = 1
    else:
        n_conditions = len(df[condition].unique())
    if cmap == 'CategoryN':
        if n_conditions <= 10:
            cmap = 'Category10'
        else:
            cmap = 'Category20'

    # Determine if colormap is discrete or continuous
    cmap_len = max(bokeh.palettes.all_palettes[cmap].keys())
    discrete_cmap = True if cmap_len < 256 else False

    if isinstance(cmap, dict) and condition is not None:
        # Sorting in hv.Curve is, somehow always, alphabetical.
        # So, generate hv.Cycle object that way.
        line_color = hv.Cycle(
            [cmap[k] for k in sorted(df[condition].unique())]
        )
    else:
        # Use Palette to nicely sample from continuous colormap
        if not discrete_cmap:
            cmap = hv.Palette(cmap, samples=n_conditions+2).values[1:-1]
        line_color = hv.Cycle(cmap)

    # Pull out available encodings (column names)
    encodings = [*list(df.columns)]

    # Set options
    base_opts = dict(
        height=height,
        width=width,
        padding=0.1,
        show_legend=legend,
        color=condition,
    )

    line_opts = base_opts
    line_opts['color'] = line_color
    scat_opts = dict(size=6, fill_alpha=0.75, tools=['hover'], cmap=cmap)
    scat_opts.update(base_opts)

    # Now, start to actually make the chart
    points = hv.Scatter(
        df,
        variable,
        [value_name, *encodings]
    )

    lines = hv.Curve(
        df,
        variable,
        [(f'mean_{value_name}', value_name),
        *encodings]
    )

    if groups:
        points = points.groupby(groups)
        lines = lines.groupby(groups)

    # Output chart as desired
    if show_points is None:
        if replicates:
            chart = lines*points
        else:
            chart = lines
    elif show_points:
        chart = lines*points
    else:
        chart = lines

    # Overlay each line plot
    if condition is not None:
        chart = chart.overlay(condition)

    chart = chart.opts({
        'Curve': line_opts,
        'Scatter': scat_opts,
    }).opts(
        legend_position='right',
        toolbar='above',
    )

    # groupby among different charts
    if groupby is not None:
        # If groupby, show as side-by-side, or dropdown
        if show_all:
            chart = chart.layout(groupby)

    return chart
