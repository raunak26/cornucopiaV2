from opentrons import protocol_api

metadata = {
    'protocolName': 'Serial Dilution Protocol - Flex',
    'author': 'OpentronsAI',
    'description': 'Perform serial dilution by transferring solution stepwise across a plate from column 1 to column 12',
    'source': 'OpentronsAI'
}

requirements = {
    'robotType': 'Flex',
    'apiLevel': '2.22'
}

def run(protocol: protocol_api.ProtocolContext):
    # Load labware
    tips = protocol.load_labware("opentrons_flex_96_tiprack_200ul", "D1")
    reservoir = protocol.load_labware("nest_12_reservoir_15ml", "D2")
    plate = protocol.load_labware("nest_96_wellplate_200ul_flat", "D3")
    
    # Load trash bin
    trash = protocol.load_trash_bin("A3")
    
    # Load pipette
    left_pipette = protocol.load_instrument("flex_1channel_1000", "right", tip_racks=[tips])

    # Distribute diluent to all wells (100 µL each)
    left_pipette.transfer(100, reservoir["A1"], plate.wells(), new_tip='once')

    # Perform serial dilution for each row
    for i in range(8):
        # Get current row
        row = plate.rows()[i]

        # Transfer solution to first well of row and mix
        left_pipette.transfer(100, reservoir["A2"], row[0], mix_after=(3, 50), new_tip='always')

        # Perform serial dilution down the row (from well to well)
        left_pipette.transfer(100, row[:11], row[1:], mix_after=(3, 50), new_tip='always')