import numpy as np
import re

def load_consumption():

    # Load consumption.txt
    consumption = np.loadtxt(open('consumption.txt', 'rb'), delimiter='\t', dtype=bytes).astype(str)

    # Remove useless rows
    consumption = consumption[np.where(np.in1d(consumption[:,0], ['ID', 'DESCRIPTION', 'UNIT', 'PARSETYPE', 'PRECISION'], invert=True))]

    # Remove useless columns
    consumption = consumption[:, np.where(np.in1d(consumption[0,:], ['Millions of tonnes of oil equivalent', 'META', 'CODE', ''], invert=True))[0]]

    # Remove redundant (summary) rows and their indicator columns
    cols_showing_redundant_rows = consumption[:, np.where(np.in1d(consumption[0,:], ['Total final consumption', 'SectorIn']))[0]]

    consumption = consumption[np.where(
        np.logical_not(np.logical_or(
            np.in1d(
                cols_showing_redundant_rows[:,0],
                ['', 'Total final consumption', '2012'],
                invert=True
            ),
            np.in1d(
                cols_showing_redundant_rows[:,1],
                ['', 'SectorIn', '2012'],
                invert=True
            )
        ))
    )[0]]

    consumption = consumption[:, np.where(np.in1d(consumption[0,:], ['Total final consumption', 'SectorIn'], invert=True))[0]]

    # Consolidate top 2 rows into single useful row and trim top row
    consumption[1, np.where(consumption[0,:] != 'Petajoules')[0]] = consumption[0, np.where(consumption[0,:] != 'Petajoules')[0]]
    consumption = consumption[1:]

    # Move categorical data cols to start of row

    consumption_categories = np.concatenate((consumption[:,:1], consumption[:,-3:]), axis=1)
    consumption = consumption[:,1:-3]

    np.savetxt('consumption.csv', np.concatenate((consumption_categories, consumption), axis=1), delimiter=',', fmt='%s')

    return consumption, consumption_categories
    
def load_balance(annual_stock_name='Annual (Short-Term) Stock'):

    balance = np.loadtxt(open('balance.txt', 'rb'), delimiter='\t', dtype=bytes).astype(str)

    # Remove useless rows
    balance = balance[np.where(np.in1d(balance[:,0], ['ID', 'DESCRIPTION', 'UNIT', 'PARSETYPE', 'PRECISION'], invert=True))]

    # Consolidate top 2 rows into single useful row and trim top row
    balance[1, np.where(balance[0,:] != 'Petajoules')[0]] = balance[0, np.where(balance[0,:] != 'Petajoules')[0]]
    balance = balance[1:, :-1]

    # Remove useless columns
    balance = balance[:, np.where(np.in1d(balance[0,:], ['Millions of tonnes of oil equivalent', 'META', 'CODE'], invert=True))[0]]

    # Remove redundant (aggregate final consumption) rows and their indicator columns
    cols_showing_redundant_rows = balance[:, np.where(balance[0,:] == 'Total final consumption')[0]]

    balance = balance[np.where(
        np.in1d(
            cols_showing_redundant_rows[:,0],
            ['', 'Total final consumption']
        )
    )[0]]

    balance = balance[:, np.where(balance[0,:] != 'Total final consumption')[0]]

    # Create empty balance metadata table
    balance_metadata = np.empty([len(balance[:,0]), 4], dtype=object)

    balance_metadata[:,0] = balance[:, 0]
    balance_metadata[:,1] = balance[:, -16]


    # Consolidate two sink columns and add in implicit annual stock sink for missing values 
    
    def fill_sink_data(row):
        #if row[0] == '' and row[1]=='':
        #    return annual_stock_name
        if row[1] == '':
            return row[0]
        else:
            return row[1]


    sink_cols = balance[:, np.where(np.in1d(balance[0], ['', ' ']))[0]] 

    sinks = []
    for row in sink_cols:
        sinks.append(fill_sink_data(row))
    sinks[0] = 'Sinks'

    balance_metadata[:, 3] = np.array(sinks)

    # Consolidate sources into single column (!!)

    ## Production and imports
    def prod_or_import(val):
        val = val[0]
        production_pattern = re.compile('prod$|production$')
        import_pattern = re.compile('imp$|import$')
        if re.search(production_pattern, val):
            return 'Primary Production'
        elif re.search(import_pattern, val):
            return 'Imports'
        else:
            return None

    production_import_col = balance[:, np.where(balance[0]=='Production and imports')]
    production_import_row_idx = np.where(production_import_col != '')

    for n in range(1,len(production_import_col)):
        balance_metadata[n, 2] = prod_or_import(production_import_col[n, 0])

    balance_metadata[production_import_row_idx, 3] = annual_stock_name 
    
    ## Stock builds and draws
    stocks_build_col = balance[:, np.where(balance[0]=='Stock changes')]
    stocks_build_row_idx = np.where(stocks_build_col != '')
    balance_metadata[stocks_build_row_idx,2] = annual_stock_name 
    balance_metadata[stocks_build_row_idx,3] = 'Long-Term Stock Changes' 

    stocks_draw_col = balance[:, np.where(balance[0]=='Stock changes out')]
    stocks_draw_row_idx = np.where(stocks_draw_col != '')
    balance_metadata[stocks_draw_row_idx,2] = 'Long-Term Stock Changes' 
    balance_metadata[stocks_draw_row_idx,3] = annual_stock_name 

    stocks_build_col = balance[:, np.where(balance[0]=='Stock  changes')]
    stocks_build_row_idx = np.where(stocks_build_col != '')
    balance_metadata[stocks_build_row_idx,2] = annual_stock_name 
    balance_metadata[stocks_build_row_idx,3] = 'Long-Term Stock Changes' 

    stocks_draw_col = balance[:, np.where(balance[0]=='Stock  change out')]
    stocks_draw_row_idx = np.where(stocks_draw_col != '')
    balance_metadata[stocks_draw_row_idx,2] = 'Long-Term Stock Changes' 
    balance_metadata[stocks_draw_row_idx,3] = annual_stock_name 

    ## Statistical difference ins and outs

    stat_diffs_neg_col = balance[:, np.where(balance[0]=='Statistical differences')]
    stat_diffs_neg_row_idx = np.where(stat_diffs_neg_col != '')
    balance_metadata[stat_diffs_neg_row_idx,2] = annual_stock_name 
    balance_metadata[stat_diffs_neg_row_idx,3] = 'Statistical Differences' 

    stat_diffs_pos_col = balance[:, np.where(balance[0]=='Statistical differences out')]
    stat_diffs_pos_row_idx = np.where(stat_diffs_pos_col != '')
    balance_metadata[stat_diffs_pos_row_idx,2] = 'Statistical Differences' 
    balance_metadata[stat_diffs_pos_row_idx,3] = annual_stock_name 

    stat_diffs_neg_col = balance[:, np.where(balance[0]=='StatisticaI differences')]
    stat_diffs_neg_row_idx = np.where(stat_diffs_neg_col != '')
    balance_metadata[stat_diffs_neg_row_idx,2] = annual_stock_name 
    balance_metadata[stat_diffs_neg_row_idx,3] = 'Statistical Differences' 

    stat_diffs_pos_col = balance[:, np.where(balance[0]=='StatisticaI difference2')]
    stat_diffs_pos_row_idx = np.where(stat_diffs_pos_col != '')
    balance_metadata[stat_diffs_pos_row_idx,2] = 'Statistical Differences' 
    balance_metadata[stat_diffs_pos_row_idx,3] = annual_stock_name 

    ## Power plants 

    power_plant_input_col = balance[:, np.where(balance[0]=='Power plants input')]
    power_plant_input_row_idx = np.where(power_plant_input_col != '')
    balance_metadata[power_plant_input_row_idx, 2] = annual_stock_name 
    balance_metadata[power_plant_input_row_idx, 3] = 'Power Plants' 

    power_plant_output_col = balance[:, np.where(balance[0]=='Power plants output')]
    power_plant_output_row_idx = np.where(power_plant_output_col != '')
    balance_metadata[power_plant_output_row_idx, 2] = 'Power Plants' 


    ## Refineries and other transformations
    refineries_other_input_col = balance[:, np.where(balance[0]=='Transformation1')]
    refineries_other_input_row_idx = np.where(refineries_other_input_col != '')
    balance_metadata[refineries_other_input_row_idx, 2] = annual_stock_name 
    balance_metadata[refineries_other_input_row_idx, 3] = refineries_other_input_col[refineries_other_input_row_idx]

    refineries_other_output_col = balance[:, np.where(balance[0]=='Transformation2')]
    refineries_other_output_row_idx = np.where(refineries_other_output_col != '')
    balance_metadata[refineries_other_output_row_idx, 2] = refineries_other_output_col[refineries_other_output_row_idx]
    balance_metadata[refineries_other_output_row_idx, 3] = annual_stock_name 

    # All remaining undefined sources / sinks default to annual stock
    for n in range(1,len(balance_metadata[:,2])):
        if balance_metadata[n,2] is None:
            balance_metadata[n,2] = annual_stock_name

    missing_sink_row_idx = np.where(balance_metadata[:, 3] == '')
    balance_metadata[missing_sink_row_idx, 3] = annual_stock_name

    # Metadata headings
    balance_metadata[0, 1] = 'Resource'
    balance_metadata[0, 2] = 'Source'
    balance_metadata[0, 3] = 'Sink'

    balance_values = balance[:,1:-16]

    np.savetxt('balance.csv', np.concatenate((balance_metadata, balance_values), axis=1), delimiter=',', fmt='%s')
    #np.savetxt('balance.csv', balance, delimiter=',', fmt='%s')

    return balance_metadata, balance_values

