import argparse, csv
import numpy as np
from eflows.load import load_consumption, load_balance
from eflows.models import Base, Resource, NodeSector, Node, Flow, resource_source_nodes, resource_sink_nodes
import eflows.template_functions as tf
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from mako.template import Template
from weasyprint import HTML
import matplotlib.pyplot as plt
from matplotlib.sankey import Sankey

parser = argparse.ArgumentParser(description='Loads, stores, and summarizes national energy flow data')

parser.add_argument('--load-data', help="Loads in national data from balance.txt and consumption.txt in current directory, saving it out to eflows.db", action="store_true")

args = parser.parse_args()

engine = create_engine('sqlite:///eflows.db')
Session = sessionmaker(bind=engine)

if args.load_data:

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

print('Generating Sankey diagrams...')
year = 1990

imports = tf.total_from_node(None, 'Imports', year) 
production = tf.total_from_node(None, 'Primary Production', year) 
stock_changes =  tf.total_from_node(None, 'Long-Term Stock Changes', year) - tf.total_into_node(None, 'Long-Term Stock Changes', year)
bunkers =  tf.total_from_node(None, 'International Bunkers', year) - tf.total_into_node(None, 'International Bunkers', year)
exports = tf.total_into_node(None, 'Exports', year) 
losses = tf.total_into_node(None, 'Power losses', year)
consumption = tf.total_final_consumption(None, year) 
stat_diffs =  tf.total_from_node(None, 'Statistical Differences', year) - tf.total_into_node(None, 'Statistical Differences', year)

cons_industry = tf.total_into_sector(None, 'Industry', year) 
cons_transport = tf.total_into_sector(None, 'Transport', year) 
cons_other = tf.total_into_sector(None, 'Other', year)
cons_other_residential = tf.total_into_node(None, 'Residential', year)
cons_other_comm_public = tf.total_into_node(None, 'Commerce and public services', year)
cons_other_other = cons_other - cons_other_residential - cons_other_comm_public
cons_non_energy_use = tf.total_into_sector(None, 'Non-energy use', year)

norm_const = imports + production + tf.total_from_node(None, 'Long-Term Stock Changes', year) + tf.total_from_node(None, 'International Bunkers', year) + tf.total_from_node(None, 'Statistical Differences', year)

fig = plt.figure(figsize=(8,5))
ax = fig.add_subplot(1, 1, 1, xticks=[], yticks=[])
ax.axis('off')

sankey = Sankey(ax=ax, scale=1/norm_const, format='%.1f', unit=' PJ', head_angle=120, margin=0.2, shoulder=0, offset=-0.05, gap=0.15, radius=0.1)

sankey.add(
        flows=[imports, production, stock_changes, bunkers, -exports, -losses, -consumption, stat_diffs],
       labels = ['Imports', 'Total Primary\nProduction', 'Stock Changes', 'International\nBunkers', 'Exports', 'Losses', 'Total Final\nConsumption', 'Statistical\n Differences'],
       orientations=[1, 0, -1, 1, 1, -1, 0, -1],
       pathlengths = [0.1, 0.1, 0.2, 0.2, 0.1, 0.2, -0.1, 0.2],
       trunklength=0.4,
       lw=0.0
)

sankey.add(
        flows=[consumption, -cons_industry, -cons_transport, -cons_non_energy_use, -cons_other],
        labels=[None, 'Industry', 'Transportation', 'Non-Energy Use', None],
        orientations=[0, 1, 1, -1, 0],
        pathlengths=[0.3, 0.1, 0.1, 0.1, -0.1],
        trunklength=0.2,
        prior=0,
        connect=(6,0), 
        lw=0.0
        
)

sankey.add(
        flows=[cons_other, -cons_other_residential, -cons_other_comm_public, -cons_other_other],
        labels=[None, 'Residential', 'Commerce and\nPublic Services', 'Other'],
        orientations=[0, 0, 1, -1],
        pathlengths=[0.1, 0.1, 0.1, 0.1],
        trunklength=0.2,
        prior=1,
        connect=(4,0), 
        lw=0.0
        
)

diagrams = sankey.finish()

for diagram in diagrams:
    diagram.patch.set_facecolor('#dddddd')
    for text in diagram.texts:
            text.set_fontsize(6)

plt.savefig('test_output.pdf', format='pdf', bbox_inches='tight', pad_inches=0)

"""
print('Generating balance tables...')
energy_balance_template = Template(filename='templates/balances.html')
years=[1973, 1990, 2010]
HTML(string=energy_balance_template.render(years=years)).write_pdf('balances.pdf')
"""

