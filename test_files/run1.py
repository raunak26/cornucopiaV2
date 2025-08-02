from opentrons import protocol_api

metadata = {
    'protocolName': 'Serial Dilution Protocol',
    'author': 'Opentrons',
    'description': 'Simple serial dilution protocol using 8-channel pipette',
    'apiLevel': '2.12'
}

def run(protocol: protocol_api.ProtocolContext):
    # Labware Setup
    tiprack_1000 = protocol.load_labware('opentrons_96_tiprack_1000ul', '1')
    dilution_plate = protocol.load_labware('corning_96_wellplate_360ul_flat', '2')
    reservoir = protocol.load_labware('usascientific_12_reservoir_22ml', '3')

    # Pipette Setup
    p1000 = protocol.load_instrument(
        'p1000_single_gen2', 
        mount='right', 
        tip_racks=[tiprack_1000]
    )

    # Serial Dilution Parameters
    dilution_factor = 2  # Example dilution factor
    mix_volume = 500  # Volume to mix in well after transfer
    transfer_volume = 1000 / dilution_factor  # Volume to transfer for dilution

    # Perform Serial Dilution
    for i in range(11):  # Assuming 12 wells are used, with the first well as the stock
        # Transfer diluent into the next well
        p1000.transfer(
            transfer_volume,
            reservoir.wells()[0],  # Assuming diluent is in the first well of the reservoir
            dilution_plate.wells()[i+1].top(),
            new_tip='always'
        )

        # Transfer from the previous well to the next to perform the dilution
        p1000.transfer(
            transfer_volume,
            dilution_plate.wells()[i],
            dilution_plate.wells()[i+1],
            mix_after=(3, mix_volume),  # Mix 3 times with mix_volume
            new_tip='always'
        )

# Note: This code is for illustrative purposes and may need to be adjusted
# depending on the specific requirements of the serial dilution.