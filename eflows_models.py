from sqlalchemy import Table, Column, Integer, String, Float, ForeignKey
from sqlalchemy.schema import ForeignKeyConstraint 
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# Data Models

class Resource(Base):
    __tablename__ = 'resources'

    name = Column(String, primary_key=True)
    flows = relationship('Flow', backref='resource')

    def __repr__(self):
        return "<Resource '%s'>" % (self.name)

class NodeSector(Base):
    __tablename__ = 'node_sectors'

    name = Column(String, primary_key=True)
    nodes = relationship('Node', backref='sector')

    def __repr__(self):
        return "<NodeSector '%s'>" % (self.name)

class Node(Base):
    __tablename__ = 'nodes'

    name = Column(String, primary_key=True)
    sector_name = Column(String, ForeignKey('node_sectors.name'))
    source_resources = relationship('Resource', secondary='resource_sink_nodes', backref='source_nodes')
    sink_resources = relationship('Resource', secondary='resource_source_nodes', backref='sink_nodes')
    source_flows = relationship('Flow', foreign_keys='[Flow.source_node_name]', backref='source_node')
    sink_flows = relationship('Flow', foreign_keys='[Flow.sink_node_name]', backref='sink_node')

    def __repr__(self):
        return "<Node '%s'>" % (self.name)

resource_source_nodes = Table(
    'resource_source_nodes', Base.metadata,
    Column('resource_name', String, ForeignKey('resources.name')),
    Column('node_name', String, ForeignKey('nodes.name'))
)

resource_sink_nodes = Table(
    'resource_sink_nodes', Base.metadata,
    Column('resource_name', String, ForeignKey('resources.name')),
    Column('node_name', String, ForeignKey('nodes.name'))
)

class Flow(Base):
    __tablename__ = 'flows'

    id = Column(Integer, primary_key=True)
    resource_name = Column(String, ForeignKey('resources.name'))
    source_node_name = Column(String, ForeignKey('nodes.name'))
    sink_node_name = Column(String, ForeignKey('nodes.name')) 
    year = Column(Integer)
    volume = Column(Float)

    ForeignKeyConstraint(
        ['resource_name', 'source_node_name'], 
        ['resource_source_nodes.resource_name','resource_source_nodes.node_name']
    )

    ForeignKeyConstraint(
        ['resource_name', 'sink_node_name'], 
        ['resource_sink_nodes.resource_name','resource_sink_nodes.node_name']
    )


