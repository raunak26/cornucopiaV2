from opentrons import protocol_api

metadata = {
    'protocolName': 'Serial Dilution',
    'author': 'Name <email@address.com>',
    'description': 'Simple serial dilution protocol',
    'apiLevel': '2.12'
}

def run(protocol: protocol_api.ProtocolContext):
    # Labware
    plate = protocol.load_labware('corning_96_wellplate_360ul_flat', '2')
    tiprack_50 = protocol.load_labware('opentrons_96_tiprack_300ul', '3')
    tiprack_1000 = protocol.load_labware('opentrons_96_tiprack_1000ul', '4')

    # Pipettes
    p50 = protocol.load_instrument('p50_multi', 'left', tip_racks=[tiprack_50])
    p1000 = protocol.load_instrument('p300_multi', 'right', tip_racks=[tiprack_1000])

    # Serial dilution
    for i in range(1, 11):
        p50.pick_up_tip()
        p50.transfer(50, plate.wells_by_name()['A' + str(i)], plate.wells_by_name()['A' + str(i+1)], mix_after=(3, 50), new_tip='never')
        p50.drop_tip()

    # Fill the first column with solution
    p1000.pick_up_tip()
    p1000.distribute(200, plate.wells_by_name()['A1'], plate.columns_by_name()['1'], new_tip='never')
    p1000.drop_tip()