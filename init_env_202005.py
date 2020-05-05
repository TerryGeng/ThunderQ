from thunderq.helper.sequence import Sequence
from thunderq.driver.AWG import AWGChannel, AWG_M3202A
from thunderq.driver.ASG import ASG_E8257C, ASG_SGS993
from thunderq.driver.acqusition import Acquisition_ATS9870
from thunderq.driver.trigger import TriggerDG645
import thunderq.runtime as runtime

# try:
#     assert isinstance(runtime.env.prob_mod_dev, AWG_M3202A)
#     assert isinstance(runtime.env.trigger_dev, TriggerDG645)
#     assert isinstance(runtime.env.probe_lo_dev, ASG_E8257C)
#     assert isinstance(runtime.env.acqusition_dev, Acquisition_ATS9870)
#     assert isinstance(runtime.env.sequence, Sequence)
# except (KeyError, AssertionError):

runtime.logger.info("Initializing DG645...")
runtime.env.trigger_dev = TriggerDG645()
runtime.logger.info("Initializing Flux M3202A chassis 1 slot 7...")
runtime.env.flux_mod_dev = AWG_M3202A(1, 7)
runtime.logger.info("Initializing Drive M3202A chassis 1 slot 5...")
runtime.env.drive_mod_dev = AWG_M3202A(1, 5)
runtime.logger.info("Initializing Probe M3202A chassis 1 slot 3...")
runtime.env.probe_mod_dev = AWG_M3202A(1, 3)
runtime.logger.info("Initializing SGS993...")
runtime.env.drive_lo_dev = ASG_SGS993()
runtime.logger.info("Initializing E8257C...")
runtime.env.probe_lo_dev = ASG_E8257C()
runtime.logger.info("Initializing ATS9870...")
runtime.env.acquisition_dev = Acquisition_ATS9870()

runtime.env.sequence = Sequence(runtime.env.trigger_dev, 5000)
runtime.logger.info("Initializing sequence...")

runtime.env.sequence.add_trigger("drive_mod_and_flux", trigger_channel="T0", raise_at=0) \
    .link_AWG_channel(AWGChannel("drive_mod_I", runtime.env.drive_mod_dev, 1)) \
    .link_AWG_channel(AWGChannel("drive_mod_Q", runtime.env.drive_mod_dev, 2)) \
    .link_AWG_channel(AWGChannel("flux_1", runtime.env.flux_mod_dev, 1)) \
    .link_AWG_channel(AWGChannel("flux_2", runtime.env.flux_mod_dev, 2)) \
    .link_AWG_channel(AWGChannel("flux_3", runtime.env.flux_mod_dev, 3)) \
    .link_AWG_channel(AWGChannel("flux_4", runtime.env.flux_mod_dev, 4))

runtime.env.sequence.add_trigger("probe_mod", trigger_channel="AB", raise_at=100e-6) \
    .link_AWG_channel(AWGChannel("probe_mod_I", runtime.env.probe_mod_dev, 1)) \
    .link_AWG_channel(AWGChannel("probe_mod_Q", runtime.env.probe_mod_dev, 2))

runtime.env.sequence.add_trigger("probe_lo", trigger_channel="CD", raise_at=100e-6)
runtime.env.sequence.add_trigger("acquisition", trigger_channel="EF", raise_at=101e-6)

runtime.env.sequence.add_slice("flux_mod", start_from=0, duration=200e-6)
runtime.env.sequence.add_slice("drive_mod", start_from=0, duration=98e-6)
runtime.env.sequence.add_slice("probe_mod", start_from=100e-6, duration=4e-6)

runtime.logger.success("Device and sequence are all initialized.")
