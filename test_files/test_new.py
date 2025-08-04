pipette = protocol.load_instrument('flex_8channel_1000', 'right')
tiprack = protocol.load_labware('opentrons_flex_96_tiprack_1000ul', 'A1')
plate = protocol.load_labware('nest_96_wellplate_200ul_flat', 'D2')
trough = protocol.load_labware('nest_12_reservoir_15ml', 'B2')
trash = protocol.load_trash_bin('D1')
water = trough.wells()[0]

for well in plate.rows()[0][:10]:
    pipette.pick_up_tip(tiprack.wells()[0])
    pipette.aspirate(20, water)
    pipette.dispense(20, well)
    pipette.drop_tip(trash)