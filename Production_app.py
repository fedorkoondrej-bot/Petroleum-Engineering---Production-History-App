import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

st.set_page_config(layout="wide") 

st.subheader('Production History for Random Wells')

# Read 10 wells data
df = pd.read_excel('10_Wells_Production_Data.xlsx', sheet_name='All_Wells')

# Calculate cumulative production and hours since interruption for each well
df = df.sort_values(['well', 'date'])
df['cum_oil'] = df.groupby('well')['oil'].cumsum()
df['cum_gas'] = df.groupby('well')['gas'].cumsum()
df['cum_water'] = df.groupby('well')['water'].cumsum()

# Convert to m3 and add revenue calculation
df['oil_m3'] = df['oil'] * 0.159  # bbl to m3
df['gas_m3'] = df['gas'] * 0.0283  # scf to m3
df['water_m3'] = df['water'] * 0.159  # bbl to m3
df['cum_oil_m3'] = df.groupby('well')['oil_m3'].cumsum()
df['cum_gas_m3'] = df.groupby('well')['gas_m3'].cumsum()
df['cum_water_m3'] = df.groupby('well')['water_m3'].cumsum()

brent_price = 80  # USD per barrel
gas_price = 3.5   # USD per MCF
df['daily_revenue'] = (df['oil'] * brent_price) + (df['gas'] / 1000 * gas_price)
df['cum_revenue'] = df.groupby('well')['daily_revenue'].cumsum()

df.date = pd.to_datetime(df.date)
df = df.sort_values(by='date', ascending=True)

# format date only to year, month, day
df.date = df.date.dt.strftime('%Y-%m-%d')

dates = df.date.unique()

# Well selector
wells = df.well.unique()
well_options = ['All Wells'] + list(wells)
selected_well = st.selectbox('Select Well', options=well_options)

# Set default date based on well selection
if selected_well == 'All Wells':
    default_date = dates[-1]
else:
    well_dates = df[df.well == selected_well]['date'].unique()
    default_date = well_dates[-1] if len(well_dates) > 0 else dates[-1]

selected_data = st.select_slider('Please Select a Date', options = dates[::-1], value=default_date)

# Create tabs
tab1, tab2 = st.tabs(["Production Data", "Production Opportunities"])

# filter for date and well
if selected_well == 'All Wells':
    df_filt = df[(df.date == selected_data) & (df.oil > 0)]
else:
    df_filt = df[(df.date == selected_data) & (df.well == selected_well) & (df.oil > 0)]

# Metrics - filtered by well selection
if selected_well == 'All Wells':
    deposit_data = df[df.date <= selected_data]
    prev_data = df[df.date < selected_data]
else:
    deposit_data = df[(df.date <= selected_data) & (df.well == selected_well)]
    prev_data = df[(df.date < selected_data) & (df.well == selected_well)]

total_oil_m3 = deposit_data.groupby('well')['cum_oil'].max().sum() * 0.159
total_gas_m3 = deposit_data.groupby('well')['cum_gas'].max().sum() * 0.0283
total_water_m3 = deposit_data.groupby('well')['cum_water'].max().sum() * 0.159
total_revenue = deposit_data.groupby('well')['cum_revenue'].max().sum()

prev_oil_m3 = prev_data.groupby('well')['cum_oil'].max().sum() * 0.159 if len(prev_data) > 0 else 0
prev_gas_m3 = prev_data.groupby('well')['cum_gas'].max().sum() * 0.0283 if len(prev_data) > 0 else 0
prev_water_m3 = prev_data.groupby('well')['cum_water'].max().sum() * 0.159 if len(prev_data) > 0 else 0
prev_revenue = prev_data.groupby('well')['cum_revenue'].max().sum() if len(prev_data) > 0 else 0

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric('Total Oil Production', f'{total_oil_m3:,.0f} m³', f'{total_oil_m3 - prev_oil_m3:+.0f} m³')
with col2:
    st.metric('Total Gas Production', f'{total_gas_m3:,.0f} m³', f'{total_gas_m3 - prev_gas_m3:+.0f} m³')
with col3:
    st.metric('Total Water Production', f'{total_water_m3:,.0f} m³', f'{total_water_m3 - prev_water_m3:+.0f} m³')
with col4:
    st.metric('Total Revenue', f'${total_revenue:,.0f}', f'${total_revenue - prev_revenue:+,.0f}')

# Reorder columns - well before date with m3 units
column_order = ['well', 'date', 'oil_m3', 'gas_m3', 'water_m3', 'daily_revenue', 'cum_oil_m3', 'cum_gas_m3', 'cum_water_m3', 'cum_revenue']
df_filt = df_filt[column_order]

st.dataframe(df_filt, use_container_width=True, height=600)

# Production history chart
st.subheader('Production History')
if selected_well == 'All Wells':
    chart_data = df.groupby('date')[['oil_m3', 'gas_m3', 'water_m3', 'daily_revenue']].sum().reset_index()
else:
    chart_data = df[df.well == selected_well][['date', 'oil_m3', 'gas_m3', 'water_m3', 'daily_revenue']]

chart_data['date'] = pd.to_datetime(chart_data['date'])

import plotly.graph_objects as go
from plotly.subplots import make_subplots

fig = make_subplots(specs=[[{"secondary_y": True}]])

fig.add_trace(go.Scatter(x=chart_data['date'], y=chart_data['oil_m3'], name='Oil (m³)', line=dict(color='black')), secondary_y=False)
fig.add_trace(go.Scatter(x=chart_data['date'], y=chart_data['gas_m3'], name='Gas (m³)', line=dict(color='green')), secondary_y=False)
fig.add_trace(go.Scatter(x=chart_data['date'], y=chart_data['water_m3'], name='Water (m³)', line=dict(color='blue')), secondary_y=False)
fig.add_trace(go.Scatter(x=chart_data['date'], y=chart_data['daily_revenue'], name='Daily Revenue'), secondary_y=True)

fig.update_yaxes(title_text="Production (m³)", secondary_y=False)
fig.update_yaxes(title_text="Revenue ($)", secondary_y=True)
fig.update_layout(title='Production History Over Time')

with tab1:
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader('Heterogeneity Index - Production Opportunities')
    
    date_data = df[df.date == selected_data]
    if len(date_data) > 0:
        avg_oil = date_data['oil_m3'].mean()
        avg_gas = date_data['gas_m3'].mean()
        avg_water = date_data['water_m3'].mean()
        
        date_data = date_data.copy()
        date_data['HI_oil'] = 1 - (date_data['oil_m3'] / avg_oil)
        date_data['HI_gas'] = 1 - (date_data['gas_m3'] / avg_gas)
        date_data['HI_water'] = abs(1 - (date_data['water_m3'] / avg_water)) + 1
        
        fig_hi = px.scatter(date_data, x='HI_oil', y='HI_gas', 
                           size='HI_water', color='well',
                           title='Heterogeneity Index - Production Opportunities',
                           labels={'HI_oil': 'Oil HI', 'HI_gas': 'Gas HI'})
        fig_hi.add_hline(y=0, line_dash="dash", line_color="red")
        fig_hi.add_vline(x=0, line_dash="dash", line_color="red")
        st.plotly_chart(fig_hi, use_container_width=True)
        
        st.write("**Interpretation:** Wells in upper-right quadrant (positive HI) have below-average production and represent improvement opportunities.")
        
        # Identify wells needing improvement
        improvement_wells = date_data[(date_data['HI_oil'] > 0) & (date_data['HI_gas'] > 0)]
        
        if len(improvement_wells) > 0:
            st.subheader('Recommended Actions')
            for _, well in improvement_wells.iterrows():
                st.write(f"**{well['well']}:**")
                actions = []
                if well['HI_oil'] > 0.3:
                    actions.append("• Consider artificial lift optimization or wellbore stimulation")
                if well['HI_gas'] > 0.3:
                    actions.append("• Evaluate gas lift system or compression optimization")
                if well['HI_water'] > 2:
                    actions.append("• Investigate water production management")
                actions.append("• Review completion design and reservoir connectivity")
                actions.append("• Consider workover operations")
                
                for action in actions:
                    st.write(action)
                st.write("")

# Show all data option
if st.checkbox('Show all data'):
    st.dataframe(df, use_container_width=True, height=400)