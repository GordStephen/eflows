import numpy as np

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
    
def load_balance():

    balance = np.loadtxt(open('balance.txt', 'rb'), delimiter='\t', dtype=bytes).astype(str)

    # Remove useless rows
    balance = balance[np.where(np.in1d(balance[:,0], ['ID', 'DESCRIPTION', 'UNIT', 'PARSETYPE', 'PRECISION'], invert=True))]

    # Remove useless columns
    balance = balance[:, np.where(np.in1d(balance[0,:], ['Millions of tonnes of oil equivalent', 'META', 'CODE'], invert=True))[0]]

    # Consolidate top 2 rows into single useful row and trim top row
    balance[1, np.where(balance[0,:] != 'Petajoules')[0]] = balance[0, np.where(balance[0,:] != 'Petajoules')[0]]
    balance = balance[1:, :-1]

    # Remove redundant (aggregate final consumption) rows and their indicator columns
    cols_showing_redundant_rows = balance[:, np.where(balance[0,:] == 'Total final consumption')[0]]

    balance = balance[np.where(
        np.in1d(
            cols_showing_redundant_rows[:,0],
            ['', 'Total final consumption']
        )
    )[0]]

    balance = balance[:, np.where(balance[0,:] != 'Total final consumption')[0]]


    np.savetxt('balance.csv', balance, delimiter=',', fmt='%s')

    return balance

