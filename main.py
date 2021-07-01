import xarray as xr
import pandas as pd
import numpy as np

# to do:
# one legend only
# tooltips
# make shareable, else screenshare
# set vmin vmax for every timestep and diff change
# add obs?

gds = xr.open_dataset('4C_EE_gds.nc').fillna(1.).rename({'experiment_id':'scenario'})

gds['scenario'] = ['no-covid','covid-fossil','covid-modgreen','covid-strgreen','covid-2yrblip']

gds = gds.sel(scenario=['no-covid','covid-2yrblip','covid-fossil','covid-modgreen','covid-strgreen'])

from bokeh.plotting import figure, show
from bokeh.io import show, output_notebook, output_file

from bokeh.models import Select, ColumnDataSource, Div
from bokeh.io import curdoc, save
from bokeh.layouts import column, row

from bokeh.models import Range1d



tools = 'box_select,hover,pan,reset,help'


header = Div(text=open("description.html").read(), sizing_mode="stretch_both")


def yearmean(ds):
    ds = ds.groupby('time.year').mean().rename({'year':'time'})
    ds['time'] = pd.date_range(start='2015-07', periods=ds.time.size, freq='12M')
    return ds


def update_plot(attrname, old, new):
    t_id = time_select.value
    m_id = member_select.value
    d_id = diff_select.value
    source2 = gen_source(gds, m_id, t_id, d_id)
    for v in gds.data_vars:
        source[v].data.update(source2[v].data)


def update_y_range(attrname, old, new):
    d_id = diff_select.value
    t_id = time_select.value
    gds = xr.open_dataset('4C_EE_gds.nc').fillna(1.).rename({'experiment_id':'scenario'})

    gds['scenario'] = ['no-covid','covid-fossil','covid-modgreen','covid-strgreen','covid-2yrblip']

    gds = gds.sel(scenario=['no-covid','covid-2yrblip','covid-fossil','covid-modgreen','covid-strgreen'])
    if t_id == 'yearly':
        gds = yearmean(gds)
    if d_id == 'True':
        gds = gds.diff('time')
    vmin = gds.min()
    vmax = gds.max()
    for v in gds.data_vars:
        y_range_start, y_range_end = get_minmax(source[v])
        plot[v].y_range.start = float(vmin[v].values)
        plot[v].y_range.end = float(vmax[v].values)



def gen_source(gds, m_id='ensemble mean (no internal variability)', t_id='yearly', d_id='False'):
    # member operation
    if m_id == 'ensemble mean (no internal variability)':
        gds = gds.mean('member_id')
    elif m_id == 'single random':
        import numpy as np
        r = np.random.randint(gds.member_id.size)
        gds = gds.isel(member_id=r)
    else:
        gds = gds.sel(member_id=m_id)

    # time operation
    if t_id == 'yearly':
        gds = yearmean(gds)

    # diff operation
    if d_id == 'True':
        gds = gds.diff('time')

    source = dict()

    for v in gds.data_vars:
        source[v] = ColumnDataSource()
        data = {s: gds.sel(scenario=s)[v].values for s in gds.scenario.values}
        data['time'] = gds.time.values
        source[v].data = data

    return source

source = gen_source(gds, t_id='yearly', m_id='r5i1p1f99')


TOOLTIPS = [
('no-covid','@no-covid'),
('covid-fossil','@covid-fossil'),
('covid-modgreen','@covid-modgreen'),
('covid-strgreen','@covid-strgreen'),
('covid-2yrblip','@covid-2yrblip')
]

colors = {'no-covid':'gray','covid-fossil':'gold','covid-modgreen':'lightgreen','covid-strgreen':'darkgreen','covid-2yrblip':'black'}


titles = {'co2': 'Global Mean Surface CO2',
          'co2_ML': 'Surface CO2 at Mauna Loa',
          'co2_emissions': 'Global CO2 emissions',
          'tas': 'Global Mean Surface Temperature (GMST)',
          'tos': 'Global Mean Sea Surface Temperature (GMSST)',
          'nino34': 'El Nino Index 3.4',
          'nbp':'Global Land CO2 flux',
          'fgco2': 'Global Ocean CO2 flux'}

fig_kwargs={'width':500, 'height':200, 'tools':tools, 'tooltips':TOOLTIPS, 'sizing_mode':"scale_both", 'x_axis_type':"datetime"}
plot_kwargs={'line_width':2, 'x':'time'}

def get_minmax(source):
    vmin = np.min([np.min(a) for a in source.data.values()][:-1])
    vmax = np.max([np.max(a) for a in source.data.values()][:-1])
    if vmin > 0 and vmax > 0:
        vmin *= 0.99
        vmax *= 1.01
    elif vmin < 0 and vmax > 0:
        vmin *= 1.01
        vmax *= 1.01
    return vmin, vmax

units = {v: gds[v].attrs['units'] for v in gds.data_vars}

def plot_band(attrname, old, new):
    d_id = diff_select.value
    t_id = time_select.value
    gds = xr.open_dataset('4C_EE_gds.nc').fillna(1.).rename({'experiment_id':'scenario'})

    gds['scenario'] = ['no-covid','covid-fossil','covid-modgreen','covid-strgreen','covid-2yrblip']

    gds = gds.sel(scenario=['no-covid','covid-2yrblip','covid-fossil','covid-modgreen','covid-strgreen'])
    if t_id == 'yearly':
        gds = yearmean(gds)
    if d_id == 'True':
        gds = gds.diff('time')
    for v in gds.data_vars:
        for scenario in gds.scenario.values:
            plot[v].varea(x=gds.time.values,
                      y1=gds[v].sel(scenario=scenario).max('member_id').values,
                      y2=gds[v].sel(scenario=scenario).min('member_id').values,
                      fill_alpha=0.05, fill_color=colors[scenario]
                      )


plot = dict()
for v in gds.data_vars:
    plot[v] = figure(title=titles[v],y_range=get_minmax(source[v]),**fig_kwargs)
    for scenario in gds.scenario.values:
        print(f'variable {v}, color {colors[scenario]}, scenario {scenario}')
        plot[v].line(y=scenario,
                     color=colors[scenario],
                     source=source[v],
                     legend_label=scenario if v=='co2_emissions' else '',
                     **plot_kwargs)

    plot[v].yaxis.axis_label = f'[{units[v]}]'
    #if v == 'co2_emissions':
    plot[v].legend.location = "top_left"
    plot[v].legend.click_policy = "hide" # mute or hide

#plot_band()

#from bokeh.layouts import gridplot
#p = gridplot([[plot['co2'], plot['co2_ML'], plot['co2_emissions']]])

diff_select = Select(value='False', title='Timestep difference', options=['True', 'False'])

time_select = Select(value='yearly', title='Timestep', options=['monthly','yearly'])

member_select = Select(value='ensemble mean (no internal variability)', title='Internal Variability', options=list(gds.member_id.values)+['single random', 'ensemble mean (no internal variability)'])


time_select.on_change('value', update_plot)
time_select.on_change('value', plot_band)
member_select.on_change('value', update_plot)
#member_select.on_change('value', plot_band)
diff_select.on_change('value', update_plot)
diff_select.on_change('value', update_y_range)
diff_select.on_change('value', plot_band)
#scenario_checkbox.on_change('value',update_plot)

controls = row(member_select, time_select, diff_select)
timeseries_co2 = column(plot['co2'], plot['co2_ML'], plot['co2_emissions'])
timeseries_carbon_sinks = column(plot['nbp'], plot['fgco2'])
timeseries_climate = column(plot['tas'], plot['tos'], plot['nino34'])

for v in ['co2_emissions','fgco2','nino34']:
    plot[v].xaxis.axis_label = 'Time'

# first was header
layout = column(header, controls, row(timeseries_co2, timeseries_carbon_sinks,timeseries_climate))

curdoc().add_root(layout)
curdoc().title = "4C explorable explanations"
