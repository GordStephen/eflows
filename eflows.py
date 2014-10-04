import argparse, csv
import numpy as np
from eflows.load import load_consumption, load_balance, load_gdp
from eflows.models import Base, Resource, NodeSector, Node, Flow, resource_source_nodes, resource_sink_nodes
import eflows.template_functions as tf
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from mako.template import Template
from weasyprint import HTML
import matplotlib.pyplot as plt
from matplotlib.sankey import Sankey
from matplotlib.patches import Rectangle

parser = argparse.ArgumentParser(description='Loads, stores, and summarizes national energy flow data')

parser.add_argument('--load-data', help="Loads in national data from balance.txt and consumption.txt in current directory, saving it out to eflows.db", action="store_true")
parser.add_argument('--generate-plots', help="Generates Sankey diagrams and time-series plots based on data stored in eflows.db", action="store_true")
parser.add_argument('--compile-report', help="Generates summary PDF with balance tables, Sankey diagrams, etc based on data stored in eflows.db and pre-generated SVG plots", action="store_true")
parser.add_argument('--run-all', help="Loads data into database, generates plots, and outputs summary report PDF", action="store_true")

args = parser.parse_args()

engine = create_engine('sqlite:///eflows.db')
Session = sessionmaker(bind=engine)

report_years = [1973, 1990, 2010, 2030, 2050]

if args.load_data or args.run_all:

    print('Clearing existing energy flows database...')
    Base.metadata.drop_all(engine)

    print('Building energy flows database schema...')
    Base.metadata.create_all(engine)
    loading_session = Session()
    loading_session.execute('pragma foreign_keys=on')

    # Load in raw data
    print('Reading in energy flows data...')
    balance_metadata, balance_values = load_balance()
    consumption, consumption_categories = load_consumption()

    # Populate models from raw data
    print('Populating database from file...')

    # Create resources
    print('  Adding resources...')
    resources = []
    for resource in np.unique(balance_metadata[1:, 1]):
        resources.append(Resource(name=resource))
    loading_session.add_all(resources)
    
    # Create consumption node sectors 
    print('  Adding consumption sectors...')
    for consumption_node_sector in np.unique(consumption_categories[1:, np.where(consumption_categories[0] == 'SectorOut')]):
        loading_session.add(NodeSector(name=consumption_node_sector))

    print('  Adding production / consumption / conversion nodes...')

    # Create basic nodes
    for node in np.unique(np.concatenate((balance_metadata[1:,2], balance_metadata[1:,3]), axis=0)):
        loading_session.add(Node(name=node))

    # Create comsumption nodes 
    consumption_nodes_names_sectors = set(map(tuple, 
        consumption_categories[1:, np.where(
            np.in1d(consumption_categories[0], ['SectorOut', 'Consumption by sector'])
        )[0]]
    ))
    consumption_nodes = []
    for sector, name in consumption_nodes_names_sectors:
        consumption_nodes.append(Node(name=name, sector_name=sector, sink_resources = resources))
    loading_session.add_all(consumption_nodes)

    print('  Adding resource flows...')

    # Add consumption flows to db
    for n in range(1,len(consumption)):
        for year_num in range(len(consumption[n])):
            loading_session.add(Flow(
                resource_name = consumption_categories[n, 1],
                source_node_name = 'Annual (Short-Term) Stock',
                sink_node_name = consumption_categories[n, 3],
                volume = float(consumption[n, year_num]),
                year = int(consumption[0, year_num])
            ))
            
    # Add balance flows to db
    for n in range(1, len(balance_values)):
        for year_num in range(len(balance_values[n])):
            loading_session.add(Flow(
                resource_name = balance_metadata[n, 1],
                source_node_name = balance_metadata[n, 2],
                sink_node_name = balance_metadata[n, 3],
                volume = float(balance_values[n, year_num]),
                year = int(balance_values[0, year_num])
            ))

    print('Database loaded successfully.')
    loading_session.commit()
    loading_session.close()

if args.generate_plots or args.run_all:

    gdp = load_gdp()
    session = Session()

    def first(iterable):
            return iterable[0]

    def custom_colourize(plot, resources):
            colour_map = {
                    'Biofuels and waste': 'darkolivegreen',
                    'Coal': 'saddlebrown',
                    'Electricity': 'dodgerblue',
                    'Geothermal': 'firebrick',
                    'Heat': 'salmon',
                    'Hydro': 'blue',
                    'Natural gas': 'darkkhaki',
                    'Nuclear': 'greenyellow',
                    'Oil': 'black',
                    'Oil products': 'dimgrey',
                    'Solar/tide/wind': 'yellow'
            }
            for resource_num in range(len(resources)):
                    plot[resource_num].set_facecolor(colour_map[resources[resource_num]]) 

    print('Generating summary plots...')

    carbon_emissions = np.zeros(np.shape(gdp))
    print(np.shape(carbon_emissions))

    def emissions(resource):

        emissions_values = {
                'Coal': 86500,
                'Natural gas': 49900,
                'Oil products': 70600 
        }

        return emissions_values.get(resource, 0)


    print('  Generating primary energy production plot...')
    years = session.query(Flow.year.distinct()).order_by(Flow.year).all() 
    years = np.array(list(map(first, years)))
    resources = tf.resources(None)

    volumes_primary = []
    resources_primary = []

    for resource in resources:
            volumes = session.query(Flow.volume).filter(Flow.source_node_name=='Primary Production', Flow.resource_name==resource).order_by(Flow.year).all()
            if len(volumes):
                resources_primary.append(resource)
                volumes_primary.append(np.array(list(map(first, volumes))))

    fig, ax = plt.subplots()
    fig.set_size_inches(8, 3.1)
    sp = ax.stackplot(years, np.row_stack(tuple(volumes_primary)), lw=0.0)
    ax.tick_params(axis='both', which='minor', labelsize=8)
    custom_colourize(sp, resources_primary)
    plt.tick_params(labelsize=8)
    plt.title('Primary Energy Production', fontsize=10)
    plt.ylabel('Petajoules', fontsize=8)
    legend_proxy_rects = [Rectangle((0, 0), 1, 1, fc=pc.get_facecolor()[0], lw=0) for pc in sp]
    plt.legend(legend_proxy_rects, resources_primary, loc='upper left', fontsize=8, frameon=False)
    plt.savefig('primary_production.svg', format='svg', bbox_inches='tight') 

    print('  Generating electricity fuel mix plot...')
    power_fuel_volumes = []
    power_fuel_names = []

    for resource in resources:
            volumes = session.query(Flow.volume).filter(Flow.sink_node_name=='Power Plants', Flow.resource_name==resource).order_by(Flow.year).all()
            if len(volumes):
                power_fuel_names.append(resource)
                power_fuel_volumes.append(np.array(list(map(first, volumes))))
                carbon_emissions = np.add(carbon_emissions, np.array(list(map(first, volumes)))*emissions(resource))

    fig, ax = plt.subplots()
    fig.set_size_inches(8, 3.1)
    sp = ax.stackplot(years, np.row_stack(tuple(power_fuel_volumes)), lw=0.0)
    custom_colourize(sp, power_fuel_names)
    plt.tick_params(labelsize=8)
    plt.title('Electricity Generation Input Fuel Mix', fontsize=10)
    plt.ylabel('Petajoules', fontsize=8)
    legend_proxy_rects = [Rectangle((0, 0), 1, 1, fc=pc.get_facecolor()[0], lw=0) for pc in sp]
    plt.legend(legend_proxy_rects, power_fuel_names, loc='upper left', fontsize=8, frameon=False)
    plt.savefig('electricity_fuel.svg', format='svg', bbox_inches='tight') 


    print('  Generating delivered energy mix plot')
    delivered_volumes = []
    delivered_names = []

    for resource in resources:
            volumes = session.execute("select sum(flows.volume) from flows, nodes where flows.resource_name='%s' and flows.sink_node_name = nodes.name and nodes.sector_name is not null group by year" % resource).fetchall()
            if len(volumes):
                delivered_names.append(resource)
                delivered_volumes.append(np.array(list(map(first, volumes))))
                carbon_emissions = np.add(carbon_emissions, np.array(list(map(first, volumes)))*emissions(resource))

    fig, ax = plt.subplots()
    fig.set_size_inches(8, 3.1)
    sp = ax.stackplot(years, np.row_stack(tuple(delivered_volumes)), lw=0.0)
    custom_colourize(sp, delivered_names)
    plt.tick_params(labelsize=8)
    plt.title('Delivered Energy Product Mix', fontsize=10)
    plt.ylabel('Petajoules', fontsize=8)
    legend_proxy_rects = [Rectangle((0, 0), 1, 1, fc=pc.get_facecolor()[0], lw=0) for pc in sp]
    plt.legend(legend_proxy_rects, delivered_names, loc='upper left', fontsize=8, frameon=False)
    plt.savefig('delivered_consumption.svg', format='svg', bbox_inches='tight') 

    print('  Generating energy imports plot')
    imported_volumes = []
    imported_names = []

    for resource in resources:
            volumes = session.execute("select sum(flows.volume) from flows where flows.resource_name='%s' and flows.source_node_name = 'Imports' group by year order by year" % resource).fetchall()
            if len(volumes):
                imported_names.append(resource)
                imported_volumes.append(np.array(list(map(first, volumes))))

    fig, ax = plt.subplots()
    fig.set_size_inches(8, 3.1)
    sp = ax.stackplot(years, np.row_stack(tuple(imported_volumes)), lw=0.0)
    custom_colourize(sp, imported_names)
    plt.tick_params(labelsize=8)
    plt.title('Energy Imports', fontsize=10)
    plt.ylabel('Petajoules', fontsize=8)
    legend_proxy_rects = [Rectangle((0, 0), 1, 1, fc=pc.get_facecolor()[0], lw=0) for pc in sp]
    plt.legend(legend_proxy_rects, imported_names, loc='upper left', fontsize=8, frameon=False)
    plt.savefig('imports.svg', format='svg', bbox_inches='tight') 


    print('  Generating energy intensity plot')

    volumes = session.execute("select sum(flows.volume) from nodes, flows where flows.sink_node_name = nodes.name and nodes.sector_name is not null group by flows.year order by flows.year").fetchall()
    volumes = np.array(list(map(first, volumes)))*1000 #Terajoules
    gdp_intensity = np.divide(volumes, gdp) # Terajoules / MegaGDP = Megajoules / GDP

    fig, ax = plt.subplots()
    fig.set_size_inches(8, 3.1)
    ax.plot(years, gdp_intensity)
    plt.tick_params(labelsize=8)
    plt.title('Energy Intensity', fontsize=10)
    plt.ylabel('Megajoules per unit GDP', fontsize=8)
    #legend_proxy_rects = [Rectangle((0, 0), 1, 1, fc=pc.get_facecolor()[0], lw=0) for pc in sp]
    #plt.legend(legend_proxy_rects, imported_names, loc='upper left', fontsize=8, frameon=False)
    plt.savefig('energy_intensity.svg', format='svg', bbox_inches='tight') 

    print('  Generating carbon intensity plot')

    volumes = session.execute("select sum(flows.volume) from nodes, flows where flows.sink_node_name = nodes.name and nodes.sector_name is not null group by flows.year order by flows.year").fetchall()
    volumes = np.array(list(map(first, volumes)))
    carbon_intensity = np.divide(carbon_emissions, volumes)

    fig, ax = plt.subplots()
    fig.set_size_inches(8, 3.1)
    ax.plot(years, carbon_intensity)
    plt.tick_params(labelsize=8)
    plt.title('Carbon Intensity', fontsize=10)
    plt.ylabel('MT CO2 per PJ converted or consumed', fontsize=8)
    #legend_proxy_rects = [Rectangle((0, 0), 1, 1, fc=pc.get_facecolor()[0], lw=0) for pc in sp]
    #plt.legend(legend_proxy_rects, imported_names, loc='upper left', fontsize=8, frameon=False)
    plt.savefig('carbon_intensity.svg', format='svg', bbox_inches='tight') 
   
    # Generate relevant Sankey diagrams
    for year in report_years:

        print('  Generating %s Sankey diagram...' % year)
        imports = tf.total_from_node(None, 'Imports', year) 
        production = tf.total_from_node(None, 'Primary Production', year) 
        stock_changes =  tf.total_from_node(None, 'Long-Term Stock Changes', year) - tf.total_into_node(None, 'Long-Term Stock Changes', year)
        bunkers =  tf.total_from_node(None, 'Bunkers', year) - tf.total_into_node(None, 'Bunkers', year)
        exports = tf.total_into_node(None, 'Exports', year) 
        losses = tf.total_into_node(None, 'Power losses', year) + tf.total_into_node(None, 'Own use', year)
        consumption = tf.total_final_consumption(None, year) 
        stat_diffs =  tf.total_from_node(None, 'Statistical Differences', year) - tf.total_into_node(None, 'Statistical Differences', year)

        norm_const = imports + production + tf.total_from_node(None, 'Long-Term Stock Changes', year) + tf.total_from_node(None, 'Statistical Differences', year)

        production_flows_full = session.query(Flow).filter(Flow.source_node_name=='Primary Production', Flow.year==year, Flow.volume > 1).all()

        num_resources = len(production_flows_full)
        production_resource_names = []
        production_resource_volumes = []

        for flow in production_flows_full:
                production_resource_names.append(flow.resource_name)
                production_resource_volumes.append(flow.volume) 

        cons_industry = tf.total_into_sector(None, 'Industry', year) 
        cons_transport = tf.total_into_sector(None, 'Transport', year) 
        cons_other = tf.total_into_sector(None, 'Other', year)
        cons_other_residential = tf.total_into_node(None, 'Residential', year)
        cons_other_comm_public = tf.total_into_node(None, 'Commerce and public services', year)
        cons_other_other = cons_other - cons_other_residential - cons_other_comm_public
        cons_non_energy_use = tf.total_into_sector(None, 'Non-energy use', year)


        fig = plt.figure(figsize=(8,5), dpi=300)
        ax = fig.add_subplot(1, 1, 1, xticks=[], yticks=[])
        ax.axis('off')

        sankey = Sankey(ax=ax, scale=2/norm_const, format='%.1f', unit=' PJ', head_angle=120, margin=0.2, shoulder=0, offset=-0.1, gap=0.15, radius=0.1)

        diagrams = sankey.add(
                flows=production_resource_volumes + [-production],
                labels=production_resource_names + [None],
                orientations=[1 if x<num_resources/2 else -1 for x in range(num_resources)] + [0],
                pathlengths=[0.1 for x in range(num_resources)] + [-0.00],
                trunklength=0.2
                
        ).add(
                flows=[imports, production, stock_changes, bunkers, -exports, -losses, -consumption, stat_diffs],
                labels = ['Imports', 'Total Primary\nProduction', 'Stock Changes', 'International\nBunkers', 'Exports', 'Own Use &\nPower Losses', None, 'Statistical\n Differences'],
                orientations=[1, 0, -1, 1, 1, -1, 0, -1],
                pathlengths = [0.2, 0.0, 0.3, 0.3, 0.2, 0.3, -0.2, 0.4],
                trunklength=0.4,
                prior=0,
                connect=(num_resources, 1)
        ).add(
                flows=[consumption, -cons_industry, -cons_transport, -cons_non_energy_use, -cons_other],
                labels=[None, 'Industry', 'Transportation', 'Non-Energy Use', None],
                orientations=[0, 1, 1, -1, 0],
                pathlengths=[0.3, 0.1, 0.1, 0.1, -0.1],
                trunklength=0.2,
                prior=1,
                connect=(6,0), 
        ).add(
                flows=[cons_other, -cons_other_residential, -cons_other_comm_public, -cons_other_other],
                labels=[None, 'Residential', 'Commerce and\nPublic Services', 'Other'],
                orientations=[0, 0, 1, -1],
                pathlengths=[0.1, 0.1, 0.1, 0.1],
                trunklength=0.2,
                prior=2,
                connect=(4,0)
        ).finish()

        for diagram in diagrams:
            diagram.patch.set_facecolor('#dddddd')
            diagram.patch.set_edgecolor('#dddddd')
            for text in diagram.texts:
                    text.set_fontsize(5)

        plt.savefig('sankey_%s.svg' % year, format='svg', bbox_inches='tight', pad_inches=0)

        session.close()


if args.compile_report or args.run_all:
    print('Compiling report:')

    print('  Generating balance tables...')
    energy_balance_template = Template(filename='templates/balances.html')

    print('  Compiling final output...')
    HTML(string=energy_balance_template.render(years=report_years)).write_pdf('balances.pdf')

    print('Report output completed successfully.')


