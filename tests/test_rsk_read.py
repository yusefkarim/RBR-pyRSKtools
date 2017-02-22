#!/usr/bin/env python3
"""
Tests for pyRSKtools RSK read methods.
"""
# Standard/external imports
import unittest
import numpy as np

# Module imports
from pyrsktools import RSK, utils
from pyrsktools.datatypes import *
from pyrsktools.channels import *
from common import RSK_FILES, GOLDEN_RSK, GOLDEN_RSK_TYPE, GOLDEN_RSK_VERSION
from common import CSV_FILES, GOLDEN_CSV
from common import MATLAB_RSK
from common import readMatlabFile, Timer, getProfileData

GOLDEN_RSK_CHANNEL_INFO = [
    ("conductivity", "mS/cm"),
    ("temperature", "°C"),
    ("pressure", "dbar"),
    ("sea_pressure", "dbar"),
    ("depth", "m"),
    ("salinity", "PSU"),
    ("speed_of_sound", "m/s"),
    ("specific_conductivity", "µS/cm"),
    ("tidal_slope", "m/hour"),
    ("significant_wave_height", "m"),
    ("significant_wave_period", "s"),
    ("one_tenth_wave_height", "m"),
    ("one_tenth_wave_period", "s"),
    ("maximum_wave_height", "m"),
    ("maximum_wave_period", "s"),
    ("average_wave_height", "m"),
    ("average_wave_period", "s"),
    ("wave_energy", "J/m²"),
]


class TestRead(unittest.TestCase):
    def test_open(self):
        # ----- Golden RSK tests -----
        self.assertTrue(GOLDEN_RSK.is_file())
        rsk = RSK(GOLDEN_RSK.as_posix())
        self.assertEqual(rsk.filename, GOLDEN_RSK.as_posix())
        self.assertEqual(rsk._db, None)
        # Open RSK
        rsk.open()
        # Db info
        self.assertEqual(rsk._reader.TYPE, GOLDEN_RSK_TYPE)
        self.assertEqual(rsk._reader.version, utils.semver2int(GOLDEN_RSK_VERSION))
        # Instrument
        self.assertEqual(rsk.instrument.serialID, 204571)
        self.assertEqual(rsk.instrument.model, "RBRconcerto³")
        self.assertEqual(rsk.instrument.firmwareVersion, "1.116")
        self.assertEqual(rsk.instrument.firmwareType, 104)
        self.assertEqual(rsk.instrument.partNumber, None)  # Part number doesn't exist for 2.0.0
        # Deployment
        self.assertEqual(rsk.deployment.deploymentID, 1)
        self.assertEqual(rsk.deployment.instrumentID, 1)
        self.assertEqual(rsk.deployment.timeOfDownload, utils.rsktime2datetime(1603763961894))
        # Channels
        self.assertEqual(len(rsk.channels), 18)
        for i, channel in enumerate(rsk.channels):
            longName, units = GOLDEN_RSK_CHANNEL_INFO[i]
            self.assertEqual(channel.longName, longName)
            self.assertEqual(channel.units, units)
        # Epoch
        self.assertEqual(rsk.epoch.deploymentID, 1)
        self.assertEqual(rsk.epoch.startTime, utils.rsktime2datetime(946684800000))
        self.assertEqual(rsk.epoch.endTime, utils.rsktime2datetime(4102358400000))
        # Schedule
        self.assertEqual(rsk.schedule.scheduleID, 1)
        self.assertEqual(rsk.schedule.instrumentID, 1)
        self.assertEqual(rsk.schedule.mode, "wave")
        self.assertEqual(rsk.schedule.gate, "twist activation")
        # Calibrations
        self.assertEqual(len(rsk.calibrations), 1)
        self.assertEqual(rsk.calibrations[0].calibrationID, 1)
        self.assertEqual(rsk.calibrations[0].channelOrder, 9)
        self.assertEqual(rsk.calibrations[0].instrumentID, 1)
        self.assertEqual(rsk.calibrations[0].type, "factory")
        self.assertEqual(rsk.calibrations[0].equation, "deri_tideslope")
        self.assertEqual(len(rsk.calibrations[0].c), 9)
        self.assertEqual(len(rsk.calibrations[0].x), 11)
        self.assertEqual(len(rsk.calibrations[0].n), 4)

        rsk.close()
        self.assertEqual(rsk._db, None)

        # ----- Generic RSK tests -----
        for f in RSK_FILES:
            with RSK(f.as_posix()) as rsk:
                # DbInfo
                self.assertIsNotNone(rsk.dbInfo)
                # Instrument
                self.assertIsNotNone(rsk.instrument)
                # Deployment
                self.assertIsNotNone(rsk.deployment)
                self.assertEqual(rsk.deployment.deploymentID, 1)
                self.assertEqual(rsk.deployment.instrumentID, 1)
                self.assertIsInstance(rsk.deployment.timeOfDownload, np.datetime64)
                # Channels
                self.assertIsNotNone(rsk.channels)
                self.assertTrue(rsk.channels != [])
                # Epoch
                self.assertIsNotNone(rsk.epoch)
                self.assertEqual(rsk.epoch.deploymentID, 1)
                self.assertIsInstance(rsk.epoch.startTime, np.datetime64)
                self.assertIsInstance(rsk.epoch.endTime, np.datetime64)
                # Schedule
                self.assertIsNotNone(rsk.schedule)
                self.assertEqual(rsk.schedule.scheduleID, 1)
                self.assertEqual(rsk.schedule.instrumentID, 1)
                # Calibrations
                self.assertIsNotNone(rsk.schedule)

    def test_readdata(self):
        # ----- Golden RSK tests -----
        columnNames = tuple(
            ["timestamp"] + [channelName for channelName, _ in GOLDEN_RSK_CHANNEL_INFO]
        )
        data0_known = np.array(
            (
                np.datetime64(1601661600000, "ms"),
                -0.000404497346607968,
                15.4990234375,
                10.1325635910034,
                6.38961791992187e-05,
                6.33751260465942e-05,
                0.0,
                1467.67993164063,
                -0.494174540042877,
                np.NaN,
                0.0,
                0.520258064516129,
                0.000782294405515432,
                0.8225,
                0.0010668166893748,
                3.654,
                0.00042476968846357,
                0.324770053475936,
                0.000576556426802489,
            )
        )

        with RSK(GOLDEN_RSK.as_posix()) as rsk:

            rsk.readdata()
            data0_loaded = np.array(rsk.data[0].tolist())
            self.assertGreater(len(rsk.data), 0)
            self.assertEqual(rsk.data.dtype.names, columnNames)
            self.assertEqual(data0_loaded.size, len(columnNames))

            self.assertTrue(
                np.allclose(
                    data0_loaded[1:].astype(np.double),
                    data0_known[1:].astype(np.double),
                    equal_nan=True,
                )
            )

        # ----- Generic RSK tests -----
        for f in RSK_FILES:
            with RSK(f.as_posix()) as rsk:
                self.assertIsInstance(rsk.data, np.ndarray)
                self.assertEqual(len(rsk.data), 0)
                rsk.readdata()
                self.assertIsInstance(rsk.data, np.ndarray)
                self.assertIsInstance(rsk.data["timestamp"][0], np.datetime64)
                self.assertIsInstance(rsk.data[0][1], np.double)
                self.assertGreater(len(rsk.data.dtype.names), 0)
                self.assertGreater(len(rsk.data), 0)

    def test_computeprofiles(self):
        # ----- Golden RSK tests -----
        with RSK(GOLDEN_RSK.as_posix()) as rsk:
            self.assertEqual(len(rsk.regions), 49)
            self.assertEqual(len(rsk.getregionsbytypes([RegionComment])), 1)
            self.assertEqual(len(rsk.getregionsbytypes([RegionGeoData])), 1)
            self.assertEqual(len(rsk.getregionsbytypes([RegionCal])), 1)
            self.assertEqual(len(rsk.getregionsbytypes([RegionExclude])), 1)

            prepopulatedProfileRegions = rsk.getregionsbytypes([RegionProfile, RegionCast])
            self.assertEqual(len(prepopulatedProfileRegions), 45)

            rsk.readdata()
            rsk.computeprofiles()
            self.assertEqual(len(rsk.regions), 49)

            # print("Number of prepopulated regions:", len(prepopulatedProfileRegions))
            # print("Number of detected regions:", len(rsk.regions))
            # TODO: See if you can get Qi to use matlabs rsktools findprofiles, so I can compare
            for i in range(min(len(rsk.regions), len(prepopulatedProfileRegions))):
                pass
                # if rsk.regions[i] != prepopulatedProfileRegions[i]:
                #     print("X ", end="")

                # print(
                #     type(rsk.regions[i]).__name__,
                #     rsk.regions[i].tstamp1.astype("uint64"),
                #     rsk.regions[i].tstamp2.astype("uint64"),
                #     type(prepopulatedProfileRegions[i]).__name__,
                #     prepopulatedProfileRegions[i].tstamp1.astype("uint64"),
                #     prepopulatedProfileRegions[i].tstamp2.astype("uint64"),
                # )
                # print(
                #     type(rsk.regions[i]),
                #     rsk.regions[i].tstamp1.astype("uint64"),
                #     rsk.regions[i].tstamp2.astype("uint64"),
                # )
                # print(
                #     type(prepopulatedProfileRegions[i]),
                #     prepopulatedProfileRegions[i].tstamp1.astype("uint64"),
                #     prepopulatedProfileRegions[i].tstamp2.astype("uint64"),
                # )

            # TODO: read profiles again but with a bunch of different combinations of
            #  pressureThreshold and conductivityThreshold, assert what we expect

        # ----- Generic RSK tests -----
        for f in RSK_FILES:
            with RSK(f.as_posix()) as rsk:
                pass  # TODO

    def test_getprofilesindices(self):
        # ----- Matlab RSK tests -----
        mRSK = readMatlabFile("RSKreadprofiles_corrected.json")
        with RSK(MATLAB_RSK.as_posix()) as rsk:
            rsk.readdata()

            for pyProfileData, mProfileData in getProfileData(rsk, mRSK):
                self.assertTrue(np.equal(pyProfileData, mProfileData).all())

        # ----- Golden RSK tests -----
        with RSK(GOLDEN_RSK.as_posix()) as rsk:
            self.assertEqual(len(rsk.regions), 49)
            rsk.readdata()

            # There are 15 profiles in the golden RSK dataset
            both = rsk.getprofilesindices()
            up = rsk.getprofilesindices(direction="up")
            down = rsk.getprofilesindices(direction="down")
            self.assertEqual(len(both), 15)
            self.assertEqual(len(up), 15)
            self.assertEqual(len(down), 15)
            self.assertEqual(len(rsk.getprofilesindices(profiles=0)), 1)
            self.assertEqual(len(rsk.getprofilesindices(profiles=[0, 1, 6])), 3)
            # Index starts at 0, 15 is out of range. Expect an error to be raised
            with self.assertRaises(ValueError):
                rsk.getprofilesindices(profiles=15)

            # Ya, ya...inefficient
            rP = [region for region in rsk.regions if type(region) in [RegionCast, RegionProfile]]
            profiles: List[Tuple[RegionCast, RegionCast, RegionProfile]] = [
                rP[i : i + 3]
                for i in range(0, len(rP), 3)
                if isinstance(rP[i], RegionCast)
                and isinstance(rP[i + 1], RegionCast)
                and isinstance(rP[i + 2], RegionProfile)
            ]
            self.assertEqual(len(profiles), len(both))
            # Go through each profile index list and check that the
            # first and last index actually match the profile start and end times.
            for i in range(len(both)):
                self.assertEqual(rsk.data["timestamp"][both[i][0]], profiles[i][2].tstamp1)
                self.assertEqual(rsk.data["timestamp"][both[i][-1]], profiles[i][2].tstamp2)
                self.assertEqual(rsk.data["timestamp"][up[i][0]], profiles[i][1].tstamp1)
                self.assertEqual(rsk.data["timestamp"][up[i][-1]], profiles[i][1].tstamp2)
                self.assertEqual(rsk.data["timestamp"][down[i][0]], profiles[i][0].tstamp1)
                self.assertEqual(rsk.data["timestamp"][down[i][-1]], profiles[i][0].tstamp2)

        # ----- Generic RSK tests -----
        for f in RSK_FILES:
            with RSK(f.as_posix()) as rsk:
                rsk.readdata()

                # If no conductivity, we can't proceed, so expect an error then move on
                if not rsk.channelexists(Conductivity):
                    with self.assertRaises(ValueError):
                        rsk.computeprofiles()
                    continue

                prepopulatedProfiles = [
                    region for region in rsk.regions if isinstance(region, RegionProfile)
                ]
                if prepopulatedProfiles:
                    self.assertEqual(len(rsk.getprofilesindices()), len(prepopulatedProfiles))

                rsk.computeprofiles()
                if rsk.regions:
                    nonProfileRegions = [
                        r for r in rsk.regions if type(r) not in [RegionCast, RegionProfile]
                    ]
                    self.assertEqual(
                        len(rsk.getprofilesindices()),
                        (len(rsk.regions) - len(nonProfileRegions)) / 3,
                    )

    def test_readprocesseddata(self):
        # ----- Golden RSK tests -----
        # Only first 8 channels are contained in burstData
        columnNames = tuple(
            ["timestamp"] + [channelName for channelName, _ in GOLDEN_RSK_CHANNEL_INFO[:8]]
        )
        data0_known = np.array(
            (
                np.datetime64(1601661600000, "ms"),
                -0.000404497346607968,
                15.4990234375,
                10.1325635910034,
                6.38961791992187e-05,
                6.33751260465942e-05,
                0.0,
                1467.67993164063,
                -0.494174540042877,
            )
        )

        with RSK(GOLDEN_RSK.as_posix()) as rsk:
            # Golden RSK has 3.5 million rows, let's just read 50_000
            rsk.readprocesseddata(t2=np.datetime64(1601690452938, "ms"))
            data0_loaded = np.array(rsk.processedData[0].tolist())
            self.assertGreater(rsk.processedData.size, 0)
            self.assertEqual(rsk.processedData.size, 50000)
            self.assertEqual(rsk.processedData.dtype.names, columnNames)
            self.assertEqual(data0_loaded.size, len(columnNames))

            self.assertTrue(
                np.allclose(
                    data0_loaded[1:].astype(np.double),
                    data0_known[1:].astype(np.double),
                    equal_nan=True,
                )
            )

        # ----- Generic RSK tests -----
        for f in RSK_FILES:
            with RSK(f.as_posix()) as rsk:
                self.assertIsInstance(rsk.processedData, np.ndarray)
                self.assertEqual(rsk.processedData.size, 0)
                if f == GOLDEN_RSK:
                    # Golden RSK is big.
                    rsk.readprocesseddata(t2=np.datetime64(1601690452938, "ms"))
                else:
                    # Let's hope the other test RSKs aren't as big =).
                    rsk.readprocesseddata()
                self.assertIsInstance(rsk.processedData, np.ndarray)
                self.assertGreater(len(rsk.processedData.dtype.names), 0)
                if len(rsk.processedData) > 0:
                    self.assertIsInstance(rsk.processedData["timestamp"][0], np.datetime64)
                    self.assertIsInstance(rsk.processedData[0][1], np.double)

    def test_csv2rsk(self):
        # ----- Golden CSV tests -----
        rsk = RSK.csv2rsk(GOLDEN_CSV.as_posix())
        self.assertEqual(len(rsk.channels), 3)
        self.assertEqual(len(rsk.data), 3)
        for i, info in enumerate(
            [
                ("conductivity", "mS/cm"),
                ("temperature", "°C"),
                ("pressure", "dbar"),
            ]
        ):
            name, unit = info[0], info[1]
            self.assertEqual(rsk.channels[i].channelID, i + 1)
            self.assertEqual(rsk.channels[i].longName, name)
            self.assertEqual(rsk.channels[i].shortName, name)
            self.assertEqual(rsk.channels[i].units, unit)
        rsk.close()

        # ----- Generic CSV tests -----
        for f in CSV_FILES:
            rsk = RSK.csv2rsk(f.as_posix())
            self.assertIsNotNone(rsk.dbInfo)
            self.assertIsNotNone(rsk.instrument)
            self.assertIsNotNone(rsk.channels)
            self.assertIsNotNone(rsk.deployment)
            self.assertIsNotNone(rsk.epoch)
            rsk.data["timestamp"]  # Make sure we can access "timestamp" data column
            self.assertIsNotNone(rsk.data)
            self.assertEqual(rsk.epoch.startTime, np.min(rsk.data["timestamp"]))
            self.assertEqual(rsk.epoch.endTime, np.max(rsk.data["timestamp"]))
            rsk.close()


if __name__ == "__main__":
    unittest.main()