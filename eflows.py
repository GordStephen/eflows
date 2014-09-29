import argparse, csv
import numpy as np
from eflows.load import load_consumption, load_balance
from eflows.models import Base, Resource, NodeSector, Node, Flow, resource_source_nodes, resource_sink_nodes
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from mako.template import Template
from weasyprint import HTML

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

energy_balance_template = Template(filename='templates/balances.html')
years=[1973]

for year in years:
    print('Generating %s balance table...' % year)
    HTML(string=energy_balance_template.render(year=year)).write_pdf('balances_%s.pdf' % year)

