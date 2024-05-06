import streamlit as st
from PIL import Image
import pandas as pd
import geopandas as gpd
import plotly.express as px
import pydeck as pdk

# global variable for county name
county_var = 'Gwinnett'

# global variables for the pydeck chropleth map
latitude_2D = 33.95737878948156
latitude_3D = 33.95737878948156
longitude_2D = -84.02506266471877
longitude_3D = -84.02506266471877
min_zoom = 8
max_zoom = 15
zoom_2D = 9.5  # lower values zoom out, higher values zoom in
zoom_3D = 10.4
map_height = 575

# set choropleth colors for the map
custom_colors = [
    '#97a3ab',  # lightest blue
    '#667883',
    '#37505d',
    '#022b3a'  # darkest blue
]

# convert the above hex list to RGB values
custom_colors = [tuple(int(h.lstrip('#')[i:i+2], 16)
                       for i in (0, 2, 4)) for h in custom_colors]

# set page configurations
st.set_page_config(
    page_title=f"{county_var} County Housing Trends",
    page_icon=":house:",
    layout="wide",
    initial_sidebar_state="expanded"
)

# the custom CSS lives here:
hide_default_format = """
        <style>
            .reportview-container .main footer {visibility: hidden;}    
            #MainMenu, footer {visibility: hidden;}
            section.main > div:has(~ footer ) {
                padding-bottom: 1px;
                padding-left: 40px;
                padding-right: 40px;
                padding-top: 20px;
            }
            [data-testid="stSidebar"] {
                padding-left: 18px;
                padding-right: 18px;
                padding-top: 0px;
                }
            [data-testid="collapsedControl"] {
                color: #FFFFFF;
                background-color: #022B3A;
                } 
            span[data-baseweb="tag"] {
                background-color: #022B3A 
                }
            div.stActionButton{visibility: hidden;}
        </style>
       """

# inject the CSS
st.markdown(hide_default_format, unsafe_allow_html=True)

# sidebarvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv

# Title of dashboard radio button for housing variable
st.sidebar.markdown(
    f"<p style='text-align:center;color:#FFFFFF;font-style:italic;'>View housing data by:</p>", unsafe_allow_html=True)

# Radio buttons for selecting the housing dashboard variable
dash_variable = st.sidebar.radio(
    label='something unimportant',
    label_visibility='collapsed',
    options=('Total sales', 'Price (per SF)', 'Price (overall)'),
    index=1
)

# dictionary for converting housing dashboard variables into actionable values to be used in the mapping functions
dash_variable_dict = {
    'Total sales': ['YearBuilt', 'count', '{:,.0f}', 'Total sales', ',.0f'],
    'Price (per SF)': ['price_sf', 'median', '${:.2f}', 'Median price (per SF)', '$.0f'],
    'Price (overall)': ['TransferAmount', 'median', '${:,.0f}', 'Median price (overall)', '$,.0f']
}

# Sidebar divider #1
st.sidebar.write("---")

# Allow user to filter data
st.sidebar.markdown(
    f"<p style='text-align:center;color:#FFFFFF;font-style:italic;'>Filter housing data by:</p>", unsafe_allow_html=True)

# Transaction year sidebar slider
years = st.sidebar.select_slider(
    'Transaction year',
    options=[
        2020,
        2021,
        2022,
        2023,
        2024
    ],
    value=(2022, 2024)
)

# dashboard main title styling variables
dash_title1_color = '#FFFFFF'
dash_title_font_size = '20'
dash_title1_font_weight = '900'
line_height1 = '12'

# dashboard year title styling variables (e.g., '2021 - 2023')
dash_title2_color = '#022B3A'
dash_title2_font_weight = '600'
line_height2 = '5'

# construct dashboard main title
if years[0] != years[1]:
    st.markdown(
        f"<h2 style='color:{dash_title1_color}; font-weight: {dash_title1_font_weight};'>{county_var} County Housing Trends | <span style='color:{dash_title2_color}; font-weight: {dash_title2_font_weight}'>{years[0]} - {years[1]}</span></h2>", unsafe_allow_html=True)
else:
    st.markdown(
        f"<h2 style='color:{dash_title1_color}; font-weight: {dash_title1_font_weight};'>{county_var} County Housing Trends | <span style='color:{dash_title2_color}; font-weight: {dash_title2_font_weight}'>{years[0]} only</span></h2>", unsafe_allow_html=True)

# construction vintage slider
year_built = st.sidebar.select_slider(
    'Year built',
    options=['<2000', '2000-2010', '2011-2023'],
    value=('<2000', '2011-2023')
)

# dictionary for filtering by construction vintage
year_built_dict = {
    '<2000': [0, 1999],
    '2000-2010': [2000, 2010],
    '2011-2023': [2011, 2050]
}

# sub-geography slider
geography_included = st.sidebar.radio(
    'Geography included',
    ('Entire county', 'City/Region'),
    index=0,
    help='Filter sales by location. Defaults to entire county. "City/Region" filter will allow multi-select of smaller groupings of Census tracts within the county.'
)

# sub-geography options
sub_geos_list = [
    'Buford/Sugar Hill',
    'Dacula',
    'Duluth',
    'Lawrenceville',
    'Lilburn',
    'NE Gwinnett',
    'Norcross/Peachtree Corners',
    'Snellville/S. Gwinnett',
    'Suwanee'
]

# Logic & select box for the sub-geographies
sub_geo = ""
if geography_included == 'City/Region':
    sub_geo = st.sidebar.multiselect(
        'Select one or more cities/regions:',
        sub_geos_list,
        ['Lawrenceville'],
    )

# Sidebar divider #2
st.sidebar.write("---")

# Map options for 2D / 3D & basemap
st.sidebar.markdown(
    f"<p style='text-align:center; color:#FFFFFF; font-style:italic; line-height:2px'>Additional map options:</p>", unsafe_allow_html=True)

# Toggle from 2D to 3D, but only if the dashboard variable is either price / SF or price (overall)
if dash_variable == 'Price (per SF)' or dash_variable == 'Price (overall)':
    map_view = st.sidebar.radio(
        'Map view',
        ('2D', '3D'),
        index=0,
        horizontal=True,
        help='Toggle 3D view to extrude map polygons showing "height" based on total number of home sales for the selected filters. Darker map colors correspond to higher median sales price / SF.'
    )
else:
    map_view = '2D'

# dropdown to select the basemap
base_map = st.sidebar.selectbox(
    'Base map',
    ('Dark', 'Light', 'Satellite', 'Streets'),
    index=3,
    help='Change underlying base map.'
)

# dictionary to change the basemap
base_map_dict = {
    'Streets': 'road',
    'Satellite': 'satellite',
    'Light': 'light',
    'Dark': 'dark'
}

# sidebar^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


@st.cache_data
def load_tab_data():
    # load the data
    df = pd.read_csv(
        'Data/Gwinnett_19-24.csv',
        thousands=',',
        keep_default_na=False,
    )

    # cast price / SF as float
    df['price_sf'] = df['price_sf'].astype(float)

    # Drop the unneeded columns
    df.drop(
        ['PropertyAddressFull', 'geometry'],
        axis=1,
        inplace=True)

    # return this item
    return df


# initialize the dataframe by running this cached function
df_init = load_tab_data()

# function to filter data for the map (by year, vintage, sub_geo) & then groupby


def filter_data_map():

    # read in dataframe
    df = df_init

    # get transaction year lower / upper bounds
    year_lower_bound = years[0]
    year_upper_bound = years[1]

    # get construction vintage lower / upper bounds
    vintage_lower_bound = year_built_dict[year_built[0]][0]
    vintage_upper_bound = year_built_dict[year_built[1]][1]

    # Now apply filters based on transaction year, construction vintage, and sub-geography (if applicable)
    if geography_included == 'City/Region':  # apply a sub-geography filter
        filtered_df = df[
            (df['year'] >= year_lower_bound) &
            (df['year'] <= year_upper_bound) &
            (df['YearBuilt'] >= vintage_lower_bound) &
            (df['YearBuilt'] <= vintage_upper_bound) &
            (df['Sub_geo'].isin(sub_geo))]
    else:  # do not apply a sub-geography filter
        filtered_df = df[
            (df['year'] >= year_lower_bound) &
            (df['year'] <= year_upper_bound) &
            (df['YearBuilt'] >= vintage_lower_bound) &
            (df['YearBuilt'] <= vintage_upper_bound)
        ]

    # now group by GEOID, i.e. Census tract
    grouped_df = filtered_df.groupby('GEOID').agg({
        # this first agg will read the dash variable and make the correct calculation
        dash_variable_dict[dash_variable][0]: dash_variable_dict[dash_variable][1],

        # this second agg will add up the total sales in each CT
        'YearBuilt': 'count',

        # this third agg will get the name of the sub geometry for each Census tract
        'Sub_geo': pd.Series.mode
    }).reset_index()

    return filtered_df, grouped_df


# function to display 2D map
def mapper_2D():

    # tabular data
    df = filter_data_map()[1]
    df['GEOID'] = df['GEOID'].astype(str)

    # read in geospatial
    gdf = gpd.read_file('Data/gwinnett_CTs_simp.geojson')

    # join together the 2, and let not man put asunder
    joined_df = gdf.merge(df, left_on='GEOID', right_on='GEOID')

    # ensure we're working with a geodataframe
    joined_df = gpd.GeoDataFrame(joined_df)

    # Drop one of the Sub_geo columns
    joined_df.drop(
        columns=['Sub_geo_x'],
        inplace=True
    )

    # Rename the other Sub_geo column
    joined_df.rename(columns={
        'Sub_geo_y': 'Sub_geo'
    }, inplace=True)

    # gonna be ugly as sin, but format the proper column
    joined_df['var_formatted'] = joined_df[dash_variable_dict[dash_variable][0]].apply(
        lambda x: dash_variable_dict[dash_variable][2].format((x)))

    # create a 'label' column for the above variable
    joined_df['dashboard_var_label'] = joined_df[dash_variable_dict[dash_variable][0]].apply(
        lambda x: dash_variable_dict[dash_variable][3].format((x)))

    # set choropleth color
    joined_df['choro_color'] = pd.cut(
        joined_df[dash_variable_dict[dash_variable][0]],
        bins=len(custom_colors),
        labels=custom_colors,
        include_lowest=True,
        duplicates='drop'
    )

    # create map intitial state
    initial_view_state = pdk.ViewState(
        latitude=latitude_2D,
        longitude=longitude_2D,
        zoom=zoom_2D,
        max_zoom=max_zoom,
        min_zoom=min_zoom,
        pitch=0,
        bearing=0,
        height=map_height
    )

    # create the geojson layer which will be rendered
    geojson = pdk.Layer(
        "GeoJsonLayer",
        joined_df,
        pickable=True,
        autoHighlight=True,
        highlight_color=[255, 255, 255, 128],
        opacity=0.5,
        stroked=True,
        filled=True,
        get_fill_color='choro_color',
        get_line_color=[255, 255, 255, 50],
        line_width_min_pixels=1
    )

    # configure & customize the tooltip
    tooltip = {
        "html": "{dashboard_var_label}: <b>{var_formatted}</b><hr style='margin: 10px auto; opacity:0.5; border-top: 2px solid white; width:85%'>\
                    Census Tract {GEOID} <br>\
                    {Sub_geo}",
        "style": {"background": "rgba(2,43,58,0.7)",
                  "border": "1px solid white",
                  "color": "white",
                  "font-family": "Helvetica",
                  "text-align": "center"
                  },
    }

    # instantiate the map object to be rendered to the Streamlit dashboard
    r = pdk.Deck(
        layers=geojson,
        initial_view_state=initial_view_state,
        map_provider='mapbox',
        map_style=base_map_dict[base_map],
        tooltip=tooltip
    )

    return r

# function to display 3D map


def mapper_3D():

    # tabular data
    df = filter_data_map()[1]
    df['GEOID'] = df['GEOID'].astype(str)

    # read in geospatial
    gdf = gpd.read_file('Data/gwinnett_CTs_simp.geojson')

    # join together the 2, and let not man put asunder
    joined_df = gdf.merge(df, left_on='GEOID', right_on='GEOID')

    # ensure we're working with a geodataframe
    joined_df = gpd.GeoDataFrame(joined_df)

    # Drop one of the Sub_geo columns
    joined_df.drop(
        columns=['Sub_geo_x'],
        inplace=True
    )

    # Rename the other Sub_geo column
    joined_df.rename(columns={
        'Sub_geo_y': 'Sub_geo'
    }, inplace=True)

    # gonna be ugly as sin, but format the proper column
    joined_df['var_formatted'] = joined_df[dash_variable_dict[dash_variable][0]].apply(
        lambda x: dash_variable_dict[dash_variable][2].format((x)))

    # create a 'label' column
    joined_df['dashboard_var_label'] = dash_variable

    # set choropleth color
    joined_df['choro_color'] = pd.cut(
        joined_df[dash_variable_dict[dash_variable][0]],
        bins=len(custom_colors),
        labels=custom_colors,
        include_lowest=True,
        duplicates='drop'
    )

    # create map intitial state
    initial_view_state = pdk.ViewState(
        latitude=latitude_3D,
        longitude=longitude_3D,
        zoom=zoom_3D,
        max_zoom=max_zoom,
        min_zoom=min_zoom,
        pitch=45,
        bearing=0,
        height=map_height
    )

    # create geojson layer
    geojson = pdk.Layer(
        "GeoJsonLayer",
        joined_df,
        pickable=True,
        autoHighlight=True,
        highlight_color=[255, 255, 255, 90],
        opacity=0.5,
        stroked=False,
        filled=True,
        wireframe=False,
        extruded=True,
        get_elevation='YearBuilt * 25',
        get_fill_color='choro_color',
        get_line_color='choro_color',
        line_width_min_pixels=1
    )

    tooltip = {
        "html": "Median {dashboard_var_label}: <b>{var_formatted}</b><br>Total sales: <b>{YearBuilt}</b><hr style='margin: 10px auto; opacity:0.5; border-top: 2px solid white; width:85%'>\
                    Census Tract {GEOID} <br>\
                    {Sub_geo}",
        "style": {"background": "rgba(2,43,58,0.7)",
                  "border": "1px solid white",
                  "color": "white",
                  "font-family": "Helvetica",
                  "text-align": "center"
                  },
    }

    r = pdk.Deck(
        layers=geojson,
        initial_view_state=initial_view_state,
        map_provider='mapbox',
        map_style=base_map_dict[base_map],
        tooltip=tooltip)

    return r

# filter the data for the line chart


def filter_data_chart():

    # read in dataframe
    df = df_init

    # get construction vintage lower / upper bounds
    vintage_lower_bound = year_built_dict[year_built[0]][0]
    vintage_upper_bound = year_built_dict[year_built[1]][1]

    # Now apply filters based on transaction year, construction vintage, and sub-geography (if applicable)
    if geography_included == 'City/Region':  # apply a sub-geography filter
        filtered_df = df[
            (df['YearBuilt'] >= vintage_lower_bound) &
            (df['YearBuilt'] <= vintage_upper_bound) &
            (df['Sub_geo'].isin(sub_geo))]
    else:  # do not apply a sub-geography filter
        filtered_df = df[
            (df['YearBuilt'] >= vintage_lower_bound) &
            (df['YearBuilt'] <= vintage_upper_bound)
        ]

    # now group by month so we get a longitudinal trend for each variable that is selected
    grouped_df = filtered_df.groupby('year-month').agg({
        # this first agg will read the dash variable and make the correct calculation
        dash_variable_dict[dash_variable][0]: dash_variable_dict[dash_variable][1],
        'month': pd.Series.mode,
        'year': pd.Series.mode
    }).reset_index()

    return grouped_df


# draw the line chart
def plotly_charter():

    # read in the filtered & grouped data
    df = filter_data_chart()

    # gonna be ugly as sin, but format the proper column
    df['var_formatted'] = df[dash_variable_dict[dash_variable][0]].apply(
        lambda x: dash_variable_dict[dash_variable][2].format((x)))

    # create a 'label' column for the above variable
    df['dashboard_var_label'] = df[dash_variable_dict[dash_variable][0]].apply(
        lambda x: dash_variable_dict[dash_variable][3].format((x)))

    # sort the data so that it's chronological
    df = df.sort_values(['year', 'month'])

    fig = px.line(
        df,
        x="year-month",
        y=dash_variable_dict[dash_variable][0],
    )

    # modify the line itself
    fig.update_traces(
        mode="lines",
        line_color='#022B3A',
        hovertemplate="<br>".join([
            "<b>%{y}</b>"
        ])
    )

    # set chart title style variables
    chart_title_font_size = '20'
    chart_title_color = '#FFFFFF'
    chart_title_font_weight = '650'

    chart_subtitle_font_size = '14'
    chart_subtitle_color = '#FFFFFF'
    chart_subtitle_font_weight = '650'

    if sub_geo == "":
        chart_title_text = f"Countywide {dash_variable_dict[dash_variable][3].lower()}"
    elif len(sub_geo) == 1:
        chart_title_text = f"{sub_geo[0]} {dash_variable_dict[dash_variable][3].lower()}"
    elif len(sub_geo) == 2:
        chart_title_text = f"{sub_geo[0]} & {sub_geo[1]} {dash_variable_dict[dash_variable][3].lower()}"
    else:
        chart_title_text = f"{dash_variable_dict[dash_variable][3]} For Selected Regions"

    # update the fig
    fig.update_layout(
        title_text=f'<span style="font-size:{chart_title_font_size}px; font-weight:{chart_title_font_weight}; color:{chart_title_color}">{chart_title_text}</span><br><span style="font-size:{chart_subtitle_font_size}px; font-weight:{chart_subtitle_font_weight}; color:{chart_subtitle_color}">(orange lines reflect range of selected years)</span>',
        title_x=0,
        title_y=0.93,
        margin=dict(
            t=85
        ),
        hoverlabel=dict(
            bgcolor="rgba(255, 255, 255, 0.8)",
            bordercolor="#022B3A",
            font_size=16,  # set the font size of the chart tooltip
            font_color="#022B3A",
            align="left"
        ),
        yaxis=dict(
            linecolor="#022B3A",
            title=None,
            tickfont_color='#022B3A',
            tickfont_size=13,
            tickformat=dash_variable_dict[dash_variable][4],
            showgrid=False,
            zeroline=False
        ),
        xaxis=dict(
            linecolor="#022B3A",
            linewidth=1,
            tickfont_color='#022B3A',
            title=None,
            tickangle=90,
            tickfont_size=13,
            tickformat='%b %Y',
            dtick='M6'
        ),
        height=450,
        hovermode="x unified")

    # add shifting vertical lines
    year_start = {
        2020: '2020-1',
        2021: '2021-1',
        2022: '2022-1',
        2023: '2023-1',
        2024: '2024-1'
    }

    year_end = {

        2020: '2020-12',
        2021: '2021-12',
        2022: '2022-12',
        2023: '2023-12',
        2024: '2024-3'
    }

    fig.add_vline(x=year_start[years[0]], line_width=2,
                  line_dash="dash", line_color="#FF8966")
    fig.add_vline(x=year_end[years[1]], line_width=2,
                  line_dash="dash", line_color="#FF8966")

    return fig


# Calculate, style KPIs-v-v-v-v-v-v-v-v-v-v-v-v-v
kpi_df = filter_data_map()[0]

# calculate & format all necessary KPI values from the filtered data
median_vintage = '{:.0f}'.format(kpi_df['YearBuilt'].median())
median_sf = '{:,.0f}'.format(kpi_df['AreaGross'].median())
total_sales = '{:,.0f}'.format(kpi_df.shape[0])
median_price_sf = '${:.0f}'.format(kpi_df['price_sf'].median())
median_price = '${:,.0f}'.format(kpi_df['TransferAmount'].median())


# calculate variables from the filtered dataframe that will drive the YoY change KPIs
df_firstYear = kpi_df[kpi_df['year'] == years[0]]
df_secondYear = kpi_df[kpi_df['year'] == years[1]]
delta_total_sales = '{:.1%}'.format((df_secondYear['price_sf'].count() -
                                     df_firstYear['price_sf'].count()) / df_firstYear['price_sf'].count())
delta_price_sf = '{:.1%}'.format((df_secondYear['price_sf'].median() -
                                  df_firstYear['price_sf'].median()) / df_firstYear['price_sf'].median())
delta_price = '{:.1%}'.format((df_secondYear['TransferAmount'].median() -
                               df_firstYear['TransferAmount'].median()) / df_firstYear['TransferAmount'].median())

# dictionary to pick out which KPI metrics to show
KPI_dict = {
    'Total sales': [total_sales, delta_total_sales],
    'Price (per SF)': [median_price_sf, delta_price_sf],
    'Price (overall)': [median_price, delta_price]
}

# kpi styles
KPI_label_font_size = '19'
KPI_label_font_color = '#FFFFFF'
KPI_label_font_weight = '700'

KPI_value_font_size = '25'
KPI_value_font_color = '#022B3A'
KPI_value_font_weight = '800'

KPI_line_height = '30'  # vertical spacing between the KPI label and value

# Calculate, style KPIs-^-^-^-^-^-^-^-^-^-^-^-^-^

# define layout columns for the dashboard
col1, col2, col3 = st.columns([
    2.9,  # map column
    0.1,  # spacer column
    2.7  # KPI / chart column
])

# draw the KPIs in the second column
with col3:
    subcol1, subcol2 = st.columns([1, 1])

    # primary metric - based on the dashboard variable
    subcol1.markdown(
        f"<span style='color:{KPI_label_font_color}; font-size:{KPI_label_font_size}px; font-weight:{KPI_label_font_weight}'>{dash_variable_dict[dash_variable][3]}</span><br><span style='color:{KPI_value_font_color}; font-size:{KPI_value_font_size}px; font-weight:{KPI_value_font_weight}; line-height: {KPI_line_height}px'>{KPI_dict[dash_variable][0]}</span>", unsafe_allow_html=True)

    # secondary metric - YoY change of dashboard variable, if applicable
    if years[0] != years[1]:
        subcol2.markdown(
            f"<span style='color:{KPI_label_font_color}; font-size:{KPI_label_font_size}px; font-weight:{KPI_label_font_weight}'>{years[0]} to {years[1]} change</span><br><span style='color:{KPI_value_font_color}; font-size:{KPI_value_font_size}px; font-weight:{KPI_value_font_weight}; line-height: {KPI_line_height}px'>{KPI_dict[dash_variable][1]}</span>", unsafe_allow_html=True)
    else:
        subcol2.markdown(
            f"<span style='color:{KPI_label_font_color}; font-size:{KPI_label_font_size}px; font-weight:{KPI_label_font_weight}'>No year over year change<br>for single year selection.</span>", unsafe_allow_html=True)

    # Metric to be kept constant regardless of dashboard variable (median vintage)
    subcol1.markdown(f"<span style='color:{KPI_label_font_color}; font-size:{KPI_label_font_size}px; font-weight:{KPI_label_font_weight}'>Median vintage</span><br><span style='color:{KPI_value_font_color}; font-size:{KPI_value_font_size}px; font-weight:{KPI_value_font_weight}; line-height: {KPI_line_height}px'>{median_vintage}</span>", unsafe_allow_html=True)

    # Metric to be kept constant regardless of dashboard variable (median SF)
    subcol2.markdown(f"<span style='color:{KPI_label_font_color}; font-size:{KPI_label_font_size}px; font-weight:{KPI_label_font_weight}'>Median size (SF)</span><br><span style='color:{KPI_value_font_color}; font-size:{KPI_value_font_size}px; font-weight:{KPI_value_font_weight}; line-height: {KPI_line_height}px'>{median_sf}</span>", unsafe_allow_html=True)

    # put a vertical spacer between the KPIs and the plotly line chart
    subcol2.write("")

# logic to draw the map & chart based on 2D / 3D selection
if map_view == '2D':
    col3.plotly_chart(plotly_charter(), use_container_width=True,
                      config={'displayModeBar': False})
    col1.pydeck_chart(mapper_2D(), use_container_width=True)
    with col1:
        expander = st.expander("Notes")
        expander.markdown(
            f"<span style='color:#022B3A'> Darker shades of Census tracts represent higher sales prices per SF for the selected time period. Dashboard excludes non-qualified, non-market, and bulk transactions. Excludes transactions below $30,000. Source: ATTOM Data Solutions.</span>", unsafe_allow_html=True)
else:
    col1.pydeck_chart(mapper_3D(), use_container_width=True)
    with col1:
        col1.markdown("<span style='color:#022B3A'><b>Shift + click</b> in 3D view to rotate and change map angle. Census tract 'height' represents total sales. Darker colors represent higher median home sale prices.</span>", unsafe_allow_html=True)
        expander = st.expander("Notes")
        expander.markdown(
            f"<span style='color:#022B3A'>Census tract 'height' representative of total sales per tract. Darker shades of Census tracts represent higher sales prices per SF for the selected time period. Dashboard excludes non-qualified, non-market, and bulk transactions. Excludes transactions below $30,000. Source: ATTOM Data Solutions.</span>", unsafe_allow_html=True)
    col3.plotly_chart(plotly_charter(), use_container_width=True,
                      config={'displayModeBar': False})

# draw logo at lower-right corner of dashboard
im = Image.open('Content/logo.png')
with col3:
    subcol1, subcol2, subcol3, subcol4 = st.columns([1, 1, 1, 1])
    subcol3.write("Powered by:")
    subcol4.image(im, width=80)
