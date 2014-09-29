from decimal import Decimal, getcontext
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine('sqlite:///eflows.db')
Session = sessionmaker(bind=engine)
session = Session()

getcontext().prec = 4

def resources(context):
    return [resource[0] for resource in session.execute("select name from resources where name <> 'Power plant losses'").fetchall()]

def resource_into_sector(context, sector_name, resource_name, year):
    val = session.execute('''select sum(volume) from flows, nodes 
            where nodes.sector_name = :sector and nodes.name = flows.sink_node_name and flows.resource_name = :resource and flows.year = :year''', {'resource':resource_name, 'sector':sector_name, 'year':year}).fetchone()[0]
    return val if val else 0.

def total_into_sector(context, sector_name, year):
    val = session.execute('''select sum(volume) from flows, nodes 
            where nodes.sector_name = :sector and nodes.name = flows.sink_node_name and flows.year = :year''', {'sector':sector_name, 'year':year}).fetchone()[0] or 0.0
    return val if val else 0.


def resource_into_node(context, node_name, resource_name, year):
    val = session.execute('select sum(volume) from flows where sink_node_name = :node and resource_name = :resource and year = :year', {'resource':resource_name, 'node':node_name, 'year':year}).fetchone()[0] or 0.0
    return val if val else 0.

def resource_from_node(context, node_name, resource_name, year):
    val = session.execute('select sum(volume) from flows where source_node_name = :node and resource_name = :resource and year = :year', {'resource':resource_name, 'node':node_name, 'year':year}).fetchone()[0] or 0.0
    return val if val else 0.

def total_into_node(context, node_name, year):
    val = session.execute('select sum(volume) from flows where sink_node_name = :node and year = :year', {'node':node_name, 'year':year}).fetchone()[0] or 0.0
    return val if val else 0.

def total_from_node(context, node_name, year):
    val = session.execute('select sum(volume) from flows where source_node_name = :node and year = :year', {'node':node_name, 'year':year}).fetchone()[0] or 0.0
    return val if val else 0.

