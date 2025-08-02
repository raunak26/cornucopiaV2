from opentrons import protocol_api

metadata = {'apiLevel': '2.12'}

def run(protocol: protocol_api.ProtocolContext):
    # Define labware
    tips_300 = protocol.load_labware('opentrons_96_tiprack_300ul', '1')
    tips_1000 = protocol.load_labware('opentrons_96_tiprack_1000ul', '2')
    plate = protocol.load_labware('corning_96_wellplate_360ul_flat', '3')

    # Define pipettes
    p50 = protocol.load_instrument('p50_multi', 'left', tip_racks=[tips_300])
    p1000 = protocol.load_instrument('p1000_multi', 'right', tip_racks=[tips_1000])

    # Define starting volume and dilution factor
    starting_volume = 50  # in uL
    dilution_factor = 2
    transfer_volume = starting_volume / dilution_factor

    # Perform serial dilution
    for i in range(11):  # 11 transfers for 12 columns
        # Pick up tips
        p50.pick_up_tip()

        # Transfer from column i to column i+1
        p50.transfer(
            transfer_volume,
            plate.columns()[i],
            plate.columns()[i+1],
            mix_after=(3, transfer_volume / 2),
            new_tip='never'
        )

        # Blow out and drop tips
        p50.blow_out(plate.columns()[i+1])
        p50.drop_tip()

        # Dilute with buffer in the next column
        p1000.pick_up_tip()
        p1000.transfer(
            starting_volume - transfer_volume,
            plate.wells_by_name()['A1'],  # Assuming A1 contains buffer
            plate.columns()[i+1],
            new_tip='never'
        )
        p1000.mix(3, starting_volume / 2, plate.columns()[i+1])
        p1000.blow_out(plate.columns()[i+1])
        p1000.drop_tip()