from agents import Agent, function_tool, ModelSettings
from utils.fixed_header import get_fixed_header

@function_tool
def generate_protocol_body(clean_prompt: str) -> str:
    # This example hardcodes a 5-step 1:2 serial dilution
    return '''
pipette = protocol.load_instrument("flex_8channel_1000", "right")
tiprack = protocol.load_labware("opentrons_flex_96_tiprack_1000ul", "A1")
plate = protocol.load_labware("nest_96_wellplate_200ul_flat", "D2")
trough = protocol.load_labware("nest_12_reservoir_15ml", "B2")
trash = protocol.load_trash_bin("D1")
pipette.tip_racks = [tiprack]

diluent = trough.wells()[0]
sample = trough.wells()[1]

# Add diluent to all wells
for well in plate.rows()[0][1:6]:
    pipette.pick_up_tip()
    pipette.aspirate(100, diluent)
    pipette.dispense(100, well)
    pipette.drop_tip()

# Add sample to first well
pipette.pick_up_tip()
pipette.aspirate(100, sample)
pipette.dispense(100, plate.rows()[0][0])
pipette.drop_tip()

# Serial dilution (1:2) across wells
for i in range(5):
    source = plate.rows()[0][i]
    dest = plate.rows()[0][i+1]
    pipette.pick_up_tip()
    pipette.aspirate(100, source)
    pipette.dispense(100, dest)
    pipette.mix(3, 100, dest)
    pipette.drop_tip()
'''
# Note: disposal volume or removal of last 100 µL can be added if needed

ProtocolGeneratorAgent = Agent(
    name="ProtocolGeneratorAgent",
    instructions=(
        "You generate only the Python code inside run(protocol): based on clean_prompt. "
        "You must use the tool generate_protocol_body. Return only raw Python code — no explanation."
    ),
    tools=[generate_protocol_body],
    output_type=str,
    model_settings=ModelSettings(temperature=0),
    tool_use_behavior="stop_on_first_tool"
)
