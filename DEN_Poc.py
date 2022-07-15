# '''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
# TestCase ID   : Video MOS Score Calculation
# Description   : Calculate anomalies occurring in video stream and use those values to calculate
#                 Video MOS Score
# Author        : Dheeraj S K
# Date          : 21 June 2022
# Version       : v1.0
# ''''''''''''''''''''[ DO NOT MODIFY ]''''''''''''''''''''''''''''''''''''''''
# ''''''''''''''''''''''''''''''''[ IMPORTS ]''''''''''''''''''''''''''''''''''
import clr, sys, os, time

clr.AddReference("System.Collections")
clr.AddReference("ScriptingLibrary")
import ScriptingLibrary
from System.Collections.Generic import List
from pathlib import Path
import base64, threading, json, re, dateutil, urllib, cv2, requests, queue
import numpy as np

#   ''''''''''''''''''''''''''''''[ END IMPORTS ]''''''''''''''''''''''''''''''
dut = ScriptingLibrary.DUT()
logger = ScriptingLibrary.Logger()
args = sys.argv
scriptPath = os.path.dirname(os.path.abspath("__file__"))
# scriptPath = os.path.realpath(__file__)
remoteFiringType = "IR"
dut.Configure(args[1], args[2], args[3], args[4], scriptPath, remoteFiringType)
logger.Configure(args[1], args[2], args[3], args[4], scriptPath)

# =============================================================================
global freeze_frame_duration, black_frame_duration, block_frame_duration, flag, video_mos_sc

black_frame_duration = 0
freeze_frame_duration = 0
block_frame_duration = 0
video_mos_sc = ""
flag = 0


class video_mos():

    def anomalies_occurrence(self, hpi_video_analysis_dur=60, black_frame=True,
                             freeze_frame=True, block_frame=False, no_of_algorithms=2, fps=1):

        # Initialisation of configs
        global freeze_frame_duration, black_frame_duration, block_frame_duration, total_duration, \
            func_exec_reg, flag

        sum_of_duration_histogram = 0
        sum_of_duration_freeze = 0
        sum_of_duration_blockers = 0
        total_count_freeze = 0
        check_duration = 60
        sum_of_duration = 0
        total_count = 0

        # """"""""""""""""""""""""""""""[ Black Frame ]""""""""""""""""""""""""""""""""""""""""
        minimum_duration_black_frame = 3000
        minimum_gap_black_frame = 0
        # """"""""""""""""""""""""""""""[ Block Frame ]"""""""""""""""""""""""""""""""""""""""""
        minimum_duration_block_frame = 800
        minimum_gap_block_frame = 0
        # """"""""""""""""""""""""""""""[ Freeze Frame ]"""""""""""""""""""""""""""""""""""""""""
        minimum_duration_freeze_frame = 5000
        minimum_gap_freeze_frame = 100
        # ''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

        result_analysis_duration = hpi_video_analysis_dur * 2

        reservationRequest = ScriptingLibrary.HighPrecisionValidationService. \
            SlotReservationRequest()
        # APTType = 1 for GetScreenTransition API alone
        # APIType = 2 for Buffering API alone
        # APIType = 12 for both GetScreenTransition API and Buffering API together
        reservationRequest.APIType = 12
        reservationResponse = dut.ReserveSlotForHPA(reservationRequest)
        logger.Log("Response - " + reservationResponse.Data.Token)
        request = ScriptingLibrary.HighPrecisionValidationService.VideoAnalysisRequest()
        deviceInfo = ScriptingLibrary.HighPrecisionValidationService.DeviceInfo()
        algorithmList = List[ScriptingLibrary.HighPrecisionValidationService.Algorithm]()
        # algorithm = ScriptingLibrary.HighPrecisionValidationService.Algorithm()
        reservationRequest = ScriptingLibrary.HighPrecisionValidationService. \
            SlotReservationRequest()
        # Maximum allowed algorithms one can use along with the script is 2.Use any of the
        # algorithm
        # listed below (alone or combined)
        reservationRequest.AlgorithmCount = no_of_algorithms
        # reservationResponse = dut.ReserveSlotForHPA(reservationRequest)
        if reservationResponse is not None:
            # ''''''''''''''''''''''''''''''''''''''''[ ALGORITHMS ]''''''''''''''''''''''''''''
            # [ Histogram (Black Frame Detection) ]
            # [ VideoFreeze ]
            # [ PerceivedVideoQuality (Video Blockers) ]
            # ''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
            if black_frame:
                # """"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
                # [ Histogram ]
                # ------------------------------------------------------------------------------
                algorithm_histogram = ScriptingLibrary.HighPrecisionValidationService.Algorithm()
                algorithm_histogram.Name = "Histogram"
                json_input = '{\
                              "rgbDetailsList": [\
                                {\
                                  "R": 0,\
                                  "G": 0,\
                                  "B": 0,\
                                  "pixelCountThreshold": 800000,\
                                  "hueTolerance": 0,\
                                  "saturationTolerance": 0,\
                                  "valueTolerance": 0\
                                }\
                              ],\
                              "maskDetails": {\
                                "xcord": 300,\
                                "ycord": 91,\
                                "width": 900,\
                                "height": 900\
                              }\
                            }'
                base64input = base64.b64encode(bytes(json_input, 'utf-8')).decode('utf-8')
                algorithm_histogram.Params = base64input
                algorithm_histogram.MinDuration = minimum_duration_black_frame
                algorithm_histogram.MinTimeGap = minimum_gap_black_frame
                algorithmList.Add(algorithm_histogram)
            if freeze_frame:
                # ==============================================================================
                # [ VideoFreeze ]
                # ------------------------------------------------------------------------------
                algorithm_freeze = ScriptingLibrary.HighPrecisionValidationService.Algorithm()
                algorithm_freeze.Name = "VideoFreeze"
                json_input = '{\
                                "Type": "MatchTemplate",\
                                "MatchScore": 0.99,\
                                "MaskDetails": {\
                                    "xcord": 300,\
                                    "ycord": 91,\
                                    "width": 900,\
                                    "height": 900\
                                }\
                            }'
                base64input = base64.b64encode(bytes(json_input, 'utf-8')).decode('utf-8')
                algorithm_freeze.Params = base64input
                algorithm_freeze.MinDuration = minimum_duration_freeze_frame
                algorithm_freeze.MinTimeGap = minimum_gap_freeze_frame
                algorithmList.Add(algorithm_freeze)
            if block_frame:
                # ==============================================================================
                # [ PerceivedVideoQuality ]
                # ------------------------------------------------------------------------------
                algorithm_blocks_detection = ScriptingLibrary.HighPrecisionValidationService. \
                    Algorithm()
                algorithm_blocks_detection.Name = "PerceivedVideoQuality"
                json_input = '{\
                                               "PredictionThreshold": 0.99,\
                                               "MaskDetails": {\
                                               "xcord": 300,\
                                               "ycord": 91,\
                                               "width": 900,\
                                               "height": 900 \
                                               }\
                                           }'
                base64input = base64.b64encode(bytes(json_input, 'utf-8')).decode('utf-8')
                algorithm_blocks_detection.Params = base64input
                algorithm_blocks_detection.MinDuration = minimum_duration_block_frame
                algorithm_blocks_detection.MinTimeGap = minimum_gap_block_frame
                algorithmList.Add(algorithm_blocks_detection)
            # ::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::
            request.FPS = fps
            # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
            request.Duration = hpi_video_analysis_dur
            request.Token = reservationResponse.Data.Token
            request.Algorithms = algorithmList
            request.DeviceInfo = deviceInfo
            response = dut.validator.StartHighPrecisionFrameAnalysis(request)
            # logger.Log("Waiting " + str(result_analysis_duration) + " seconds to complete "
            #                                                         "video analysis")
            # time.sleep(result_analysis_duration)

            logger.Log("Result analysis duration : " + str(result_analysis_duration))
            for index in range(int(result_analysis_duration)):
                logger.Log(str(index) + " sec Analysing data for " + str(result_analysis_duration))
                time.sleep(1)

            if response is not None:
                logger.Log(
                    "StartHighPrecisionFrameAnalysis Response Token - " + response.Data.Token)
                statusRequest = ScriptingLibrary.HighPrecisionValidationService. \
                    VideoAnalysisStatusRequest()
                statusRequest.Token = response.Data.Token
                istarttime = time.time()
                iendtime = time.time()
                while (iendtime - istarttime) < check_duration:
                    iendtime = time.time()
                    statusResponse = dut.validator.GetHighPrecisionFrameAnalysisResult(
                        statusRequest)
                    # dut.validator.StopHighPrecisionFrameAnalysis(response.Data.Token)
                    logger.Log("StatusResponse - " + str(statusResponse))
                    if statusResponse is not None and statusResponse.Data is not None and \
                            statusResponse.Data.Count > 0 and statusResponse.Status == \
                            'Completed':
                        # buffering API response ready
                        buffering_check_completed = True
                        logger.Log("Response - Captured URL Links")
                        break
                for data in statusResponse.Data:
                    logger.Log("Getting data for each algorithm :- " + str(data.AlgorithmData))
                    for algorithm_data in data.AlgorithmData:
                        sum_of_duration += algorithm_data.Duration
                        total_count += 1
                        logger.Log("Response - Captured URL Link")
                        logger.Log("DEBUG : " + str(algorithm_data.StartingImage))
                        if data.AlgorithmName == "Histogram":
                            sum_of_duration_histogram += algorithm_data.Duration
                            logger.Log("Link to the Captured buffer black frame :- ")
                            logger.Log(str(algorithm_data.StartingImage))
                        elif data.AlgorithmName == "VideoFreeze":
                            sum_of_duration_freeze += algorithm_data.Duration
                            total_count_freeze += 1
                            logger.Log("Link to the Captured buffer video freeze :- ")
                            logger.Log(str(algorithm_data.StartingImage))
                        else:
                            sum_of_duration_blockers += algorithm_data.Duration
                            logger.Log("Link to the Captured buffer video block :- ")
                            logger.Log(str(algorithm_data.StartingImage))
                if block_frame:
                    block_frame_duration = block_frame_duration + sum_of_duration_blockers
                else:
                    black_frame_duration = black_frame_duration + sum_of_duration_histogram
                    freeze_frame_duration = freeze_frame_duration + sum_of_duration_freeze
                logger.Log("Analysis ended...")

            else:
                logger.Log("StartHighPrecisionFrameAnalysis API Failed")
        else:
            logger.Log("ReserveSlotForHPA API failed")
        # updating flag
        flag = flag + 1

    def get_duration_in_secs(self, original_dur="00:00:00"):
        # converting hh:mm:ss in to seconds
        hours, minutes, seconds = str(original_dur).split(":")
        original_dur_secs = round(int(hours) * 3600 + int(minutes) * 60 + float(seconds), 2)
        logger.Log("Analysis duration provided in seconds : " + str(original_dur_secs))
        return original_dur_secs

    def get_loop_count(self, duration):
        if duration <= 600:
            lp_count = 0
        else:
            lp_count = round(duration / 600)
        return lp_count

    def report(self):
        global freeze_frame_duration, black_frame_duration, block_frame_duration, video_mos_sc
        logger.Log("\n")
        logger.Log(" ------------------------[FINAL REPORT]-------------------------")
        logger.Log(" * Black frame duration  :- " + str(black_frame_duration) + " milliseconds")
        logger.Log(" * Freeze frame duration :- " + str(freeze_frame_duration) + " milliseconds")
        logger.Log(" * Block frame duration  :- " + str(block_frame_duration) + " milliseconds")
        logger.Log(" * VIDEO MOS SCORE :- " + str(video_mos_sc))
        logger.Log(" ----------------------------------------------------------------------------")
        logger.Log("\n")
        if not os.path.exists("Report"):
            os.mkdir("Report")
        file_name = "den_video_anomalies_report.xlsx"

    def mos_calculate(self):
        global freeze_frame_duration, black_frame_duration, block_frame_duration, video_mos_sc
        logger.Log("\n")
        logger.Log("<<<<<<<<<<<<<<<<<<<< [Calculating MOS Score] >>>>>>>>>>>>>>>>>>>>")
        # Eq :-  BF = t/1000  t -> total black frame duration
        black_frame_severity_factor = black_frame_duration / 1000
        # Eq :-  FF = t/1000  t -> total freeze frame duration
        freeze_frame_severity_factor = freeze_frame_duration / 1000
        # Eq :-  B = t/1000  t -> total block frame duration
        block_frame_severity_factor = block_frame_duration / 1000
        # Eq :-  va = BF + FF
        total_severity_factor = black_frame_severity_factor + freeze_frame_severity_factor + \
                                block_frame_severity_factor
        # Eq :-  v_mos = 1 - va
        video_mos_sc = 1 - total_severity_factor
        # if mos is < 0 we will consider it as 0
        if video_mos_sc < 0:
            video_mos_sc = 0


if __name__ == '__main__':

    # config initialisation
    one_minute = 60
    ten_second = 10
    five_second = 5
    thread_start_time = 10
    number_of_algorithms_exec = 3

    # creating class object
    mos = video_mos()
    # get duration in seconds
    video_analysis_duration = mos.get_duration_in_secs(original_dur="04:00:00")
    # get the maximum number of timer loop needs to run
    max_loop_count = mos.get_loop_count(duration=video_analysis_duration)
    if video_analysis_duration > 600:
        hpi_video_analysis_dur = 600
    else:
        hpi_video_analysis_dur = video_analysis_duration

    logger.Log("Max loop count : " + str(max_loop_count))
    logger.Log("HPI Analysis duration : " + str(hpi_video_analysis_dur))
    logger.Log("Total analysis duration : " + str(video_analysis_duration))
    time.sleep(ten_second)

    # Threading the HPA api
    threading.Timer(thread_start_time, mos.anomalies_occurrence, [hpi_video_analysis_dur]).start()
    if number_of_algorithms_exec == 3:
        time.sleep(five_second)
        threading.Timer(thread_start_time, mos.anomalies_occurrence, [hpi_video_analysis_dur, False,
                                                                      False, True, 1, 1]).start()
    time.sleep(hpi_video_analysis_dur)
    if video_analysis_duration > 600:
        for i in range(max_loop_count - 1):
            threading.Timer(thread_start_time, mos.anomalies_occurrence,
                            [hpi_video_analysis_dur]).start()
            if number_of_algorithms_exec == 3:
                time.sleep(five_second)
                threading.Timer(thread_start_time, mos.anomalies_occurrence,
                                [hpi_video_analysis_dur, False, False, True, 1, 1]).start()
            time.sleep(hpi_video_analysis_dur)

    # calculate the flag threshold value for getting the report
    if number_of_algorithms_exec == 3:
        if max_loop_count == 0:
            flag_threshold = 2
        else:
            flag_threshold = max_loop_count * 2
    else:
        if max_loop_count == 0:
            flag_threshold = 1
        else:
            flag_threshold = max_loop_count

    # **************************************[ Final Report ]**************************************
    if max_loop_count == 0:
        for retry in range(200):
            if flag != flag_threshold:
                logger.Log("Script Execution not ended, waiting for result....")
                time.sleep(one_minute)
            else:
                mos.mos_calculate()
                mos.report()
                break
    else:
        for retry in range(200):
            if flag != flag_threshold:
                logger.Log("Script Execution not ended, waiting for result....")
                time.sleep(one_minute)
            else:
                mos.mos_calculate()
                mos.report()
                break
