# -*- coding: utf-8 -*-
# MooQuant
#
# Copyright 2017 bopo.wang<ibopo@126.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
.. moduleauthor:: BoPo Wang <ibopo@126.com>
"""

import datetime

from mooquant import bar
from mooquant.barfeed import common, csvfeed
from mooquant.utils import dt


# Google Finance CSV parser
# Each bar must be on its own line and fields must be separated by comma (,).
#
# Bars Format:
# Date,Open,High,Low,Close,Volume
#
# The csv Date column must have the following format: D-B-YY
def parse_date(date):
    date = date.split("-")
    ret = datetime.datetime(int(date[0]), int(date[1]), int(date[2]))

    return ret


class RowParser(csvfeed.RowParser):
    def __init__(self, dailyBarTime, frequency, timezone=None, sanitize=False):
        self.__dailyBarTime = dailyBarTime
        self.__frequency = frequency
        self.__timezone = timezone
        self.__sanitize = sanitize

    def __parseDate(self, dateString):
        ret = parse_date(dateString)
        # Time on Google Finance CSV files is empty. If told to set one, do it.
        if self.__dailyBarTime is not None:
            ret = datetime.datetime.combine(ret, self.__dailyBarTime)

        # Localize the datetime if a timezone was given.
        if self.__timezone:
            ret = dt.localize(ret, self.__timezone)

        return ret

    def getFieldNames(self):
        # It is expected for the first row to have the field names.
        return None

    def getDelimiter(self):
        return ","

    def parseBar(self, csvRowDict):
        dateTime = self.__parseDate(csvRowDict["Date"])
        close = float(csvRowDict["Close"])
        open_ = float(csvRowDict["Open"])
        high = float(csvRowDict["High"])
        low = float(csvRowDict["Low"])
        volume = float(csvRowDict["Volume"])
        adjClose = None

        if self.__sanitize:
            open_, high, low, close = common.sanitize_ohlc(open_, high, low, close)

        return bar.BasicBar(dateTime, open_, high, low, close, volume, adjClose, self.__frequency)


class Feed(csvfeed.BarFeed):
    """A :class:`mooquant.barfeed.csvfeed.BarFeed` that loads bars from CSV files downloaded from Google Finance.

    :param frequency: The frequency of the bars. Only **mooquant.bar.Frequency.DAY** is currently supported.
    :param timezone: The default timezone to use to localize bars. Check :mod:`mooquant.marketsession`.
    :type timezone: A pytz timezone.
    :param maxLen: The maximum number of values that the :class:`mooquant.dataseries.bards.BarDataSeries` will hold.
        Once a bounded length is full, when new items are added, a corresponding number of items are discarded from the
        opposite end. If None then dataseries.DEFAULT_MAX_LEN is used.
    :type maxLen: int.

    .. note::
        Google Finance csv files lack timezone information.
        When working with multiple instruments:

            * If all the instruments loaded are in the same timezone, then the timezone parameter may not be specified.
            * If any of the instruments loaded are in different timezones, then the timezone parameter must be set.
    """

    # frequency == 频率
    def __init__(self, frequency=bar.Frequency.DAY, timezone=None, maxLen=None):
        if frequency not in [bar.Frequency.DAY]:
            raise Exception("Invalid frequency.")

        super().__init__(frequency, maxLen)

        self.__timezone = timezone
        self.__sanitizeBars = False

    # 标准化函数
    def sanitizeBars(self, sanitize):
        self.__sanitizeBars = sanitize

    def barsHaveAdjClose(self):
        return False

    def addBarsFromCSV(self, instrument, path, timezone=None):
        """Loads bars for a given instrument from a CSV formatted file.
        The instrument gets registered in the bar feed.

        :param instrument: Instrument identifier.
        :type instrument: string.
        :param path: The path to the CSV file.
        :type path: string.
        :param timezone: The timezone to use to localize bars. Check :mod:`mooquant.marketsession`.
        :type timezone: A pytz timezone.
        """

        if timezone is None:
            timezone = self.__timezone

        rowParser = RowParser(self.getDailyBarTime(), self.getFrequency(), timezone, self.__sanitizeBars)
        super().addBarsFromCSV(instrument, path, rowParser)
