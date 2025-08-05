"""DETAILS."""

metadata = {
    'protocolName': 'Test Da Water',
    'author': 'Opentrons <protocols@opentrons.com>',
    'source': 'Protocol Library'
}

requirements = {
    "robotType": "Flex",
    "apiLevel": "2.19"
}
def add_parameters(parameters):

    get_choices_deck_slots = lambda: [{"display_name": str(i), "value": i } for i in [f"{chr(ord('A') + i)}{j}" for i in range(4) for j in range(1, 5)]]

    parameters.add_str(
        variable_name = "pipette_type", display_name = "Pipette Type", default = "flex_1channel_1000", choices = [
            {"display_name": "Flex P1000 8-Channel Pipette", "value": "flex_8channel_1000"},
            {"display_name": "Flex P50 8-Channel Pipette", "value": "flex_8channel_50"},
            {"display_name": "Flex P1000 1-Channel Pipette", "value": "flex_1channel_1000"},
            {"display_name": "Flex P50 1-Channel Pipette", "value": "flex_1channel_50"} ]
    )
    parameters.add_str(
        variable_name = "mount_side", display_name = "Mount Side", default = "right", choices = [
            {"display_name": "Left", "value": "left"},
            {"display_name": "Right", "value": "right"}
        ]
    )
    parameters.add_str(
        variable_name = "tip_type", display_name = "Tip Type", default = "1000f", choices = [
            {"display_name": "Opentrons 1000 uL Filter", "value": "1000f"},
            {"display_name": "Opentrons 1000 uL Standard", "value": "1000"},
            {"display_name": "Opentrons 200 uL Filter", "value": "200f"},
            {"display_name": "Opentrons 200 uL Standard", "value": "200"},
            {"display_name": "Opentrons 50 uL Filter", "value": "50f"},
            {"display_name": "Opentrons 50 uL Standard", "value": "50"}
        ]
    )

    parameters.add_str(
        variable_name = "tip_1_slot", display_name = "Tiprack 1 Deck Slot", default = "C1", choices = get_choices_deck_slots()
    )

    parameters.add_str(
        variable_name = "tip_2_slot", display_name = "Tiprack 2 Deck Slot", default = "D1", choices = get_choices_deck_slots()
    )
    parameters.add_str(
        variable_name = "trough_type", display_name = "Trough Type", default = "nest_12_reservoir_15ml", choices = [
            {"display_name": "NEST 12-Well, 15mL", "value": "nest_12_reservoir_15ml"},
            {"display_name": "USA Scientific 12-Well, 22mL", "value": "usascientific_12_reservoir_22ml"}
        ]
    )

    parameters.add_str(
        variable_name = "trough_slot", display_name = "Trough Deck Slot", default = "D2", choices = get_choices_deck_slots()
    )

    parameters.add_str(
        variable_name = "plate_type", display_name = "Plate Type", default = "nest_96_wellplate_200ul_flat", choices = [
            {"display_name": "NEST 96-Well, 200uL Flat", "value": "nest_96_wellplate_200ul_flat"},
            {"display_name": "Corning 96-Well, 360uL Flat", "value": "corning_96_wellplate_360ul_flat"},
            {"display_name": "NEST 96-Well, 100uL PCR", "value": "nest_96_wellplate_100ul_pcr_full_skirt"},
            {"display_name": "Bio-Rad 96-Well, 200uL PCR", "value": "biorad_96_wellplate_200ul_pcr"}
        ]
    )

    parameters.add_str(
        variable_name = "plate_slot", display_name = "Plate Deck Slot", default = "D3", choices = get_choices_deck_slots()
    )

    parameters.add_int(
        variable_name = "dilution_factor", display_name = "dilution factor", default = 3, minimum = 1, maximum = 3
    )
    parameters.add_int(
        variable_name = "num_of_dilutions", display_name = "number of dilutions", default = 10, minimum = 1, maximum = 11
    )
    parameters.add_float(
        variable_name = "total_mixing_volume", display_name = "total mixing volume (in uL)", default = 150, minimum = 15, maximum = 150
    )
    parameters.add_bool(
        variable_name = "blank_on", display_name = "Blank in Well Plate", default = False
    )
    parameters.add_str(
        variable_name = "tip_use_strategy", display_name = "tip use strategy", default = "never", choices = [
            {"display_name": "use one tip", "value": "never"},
            {"display_name": "change tips", "value": "always"}
        ]
    )

    parameters.add_str(
        variable_name = "waste_type", display_name = "Waste Container Type", default = "trash_bin", choices = [
            {"display_name": "trash bin", "value": "trash_bin"},
            {"display_name": "waste chute", "value": "waste_chute"}
        ]
    )
    parameters.add_int(
        variable_name = "air_gap_volume", display_name = "volume of air gap", default = 10, minimum = 0, maximum = 10
    )

def run(protocol_context):
    # Set fixed parameters as per user request
    pipette_type = "flex_8channel_1000"
    mount_side = "right"
    tip_type = "1000"
    tip_1_slot = "A1"
    plate_slot = "D2"
    trough_slot = "B2"
    trash_slot = "D1"

    tip_types_dict = {
        '1000': 'opentrons_flex_96_tiprack_1000ul',
    }

    # Load labware
    tip_name = tip_types_dict[tip_type]
    tiprack = protocol_context.load_labware(tip_name, tip_1_slot)
    plate = protocol_context.load_labware("nest_96_wellplate_200ul_flat", plate_slot)
    trough = protocol_context.load_labware("nest_12_reservoir_15ml", trough_slot)
    trash = protocol_context.load_trash_bin(trash_slot)

    # Load pipette
    pipette = protocol_context.load_instrument(pipette_type, mount_side, [tiprack])

    # Use first well of trough for water
    water = trough.wells()[0]

    # For each well in the first row of the plate
    for well in plate.rows()[0]:
        protocol_context.delay(seconds=60)
        pipette.pick_up_tip()
        pipette.aspirate(100, water)
        pipette.dispense(100, well)
        pipette.drop_tip(trash)