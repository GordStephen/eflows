import argparse, csv
import numpy as np
from eflows_load import load_consumption, load_balance
from eflows_models import Base, Resource, NodeSector, Node, Flow, resource_source_nodes, resource_sink_nodes
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

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

    # Load in raw data
    print('Reading in energy flows data...')
    balance = load_balance()
    consumption, consumption_categories = load_consumption()

    # Populate models from raw data
    print('Populating database from file...')

    # Create resources
    print('  Adding resources...')
    resources = []
    for resource in np.unique(balance[1:, np.where(balance[0] == 'Product')]):
        resources.append(Resource(name=resource))
    loading_session.add_all(resources)
    
    # Create consumption node sectors 
    print('  Adding consumption sectors...')
    for consumption_node_sector in np.unique(consumption_categories[1:, np.where(consumption_categories[0] == 'SectorOut')]):
        loading_session.add(NodeSector(name=consumption_node_sector))

    print('  Adding production / consumption / conversion nodes...')

    # Create basic nodes
    production = Node(name='Primary Production', source_resources = resources)
    imports = Node(name='Imports', source_resources = resources)
    loading_session.add_all([production, imports])

    annual_stock = Node(name='Annual (Short-Term) Stock', source_resources = resources, sink_resources = resources)
    stocks = Node(name='Long-Term Stocks', source_resources = resources, sink_resources = resources)
    stat_diff = Node(name='Statistical Differences', source_resources = resources, sink_resources = resources)
    power = Node(name='Power Plants', source_resources = resources, sink_resources = resources) #TODO Limit source resources
    refineries = Node(name='Refineries', source_resources = resources, sink_resources = resources) #TODO Limit source / sink resources
    other_conv = Node(name='Other Conversions', source_resources = resources, sink_resources = resources)
    loading_session.add_all([annual_stock, stocks, stat_diff, power, refineries, other_conv])

    exports = Node(name='Exports', sink_resources = resources)
    bunkers = Node(name='International Bunkers', sink_resources = resources)
    power_loss = Node(name='Power Loss', sink_resources=resources)
    loading_session.add_all([exports, bunkers, power_loss])

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


    # Add allowed resource source / sink nodes

    # Add consumption flows to db
    print('  Adding resource flows...')
    for n in range(1,len(consumption)):
        
        for year_num in range(len(consumption[n])):
            loading_session.add(Flow(
                name = consumption_categories[n, 0] + consumption[0, year_num],
                resource_name = consumption_categories[n, 1],
                source_node_name = 'Annual (Short-Term) Stock',
                sink_node_name = consumption_categories[n, 3],
                volume = float(consumption[n, year_num]),
                year = int(consumption[0, year_num])
            ))
            
    for n in range(1, len(balance)):
        pass   

    loading_session.commit()
    loading_session.close()
    #print('Database loaded.')

session = Session()
# Read values, generate plots, tables, etc
session.close()


