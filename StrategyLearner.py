"""
Template for implementing StrategyLearner  (c) 2016 Tucker Balch

Copyright 2018, Georgia Institute of Technology (Georgia Tech)
Atlanta, Georgia 30332
All Rights Reserved

Template code for CS 4646/7646

Georgia Tech asserts copyright ownership of this template and all derivative
works, including solutions to the projects assigned in this course. Students
and other users of this template code are advised not to share it with others
or to make it available on publicly viewable websites including repositories
such as github and gitlab.  This copyright statement should not be removed
or edited.

We do grant permission to share solutions privately with non-students such
as potential employers. However, sharing with other current or future
students of CS 7646 is prohibited and subject to being investigated as a
GT honor code violation.

-----do not edit anything above this line---

Student Name: Ryan Miller
GT User ID: rmiller327
GT ID: 903461824
"""

import datetime as dt
import pandas as pd
import util as ut
from BagLearner import BagLearner
from RTLearner import RTLearner
from indicators import *

class StrategyLearner(object):
    def __init__(self, verbose = False, impact = 0.0,
                 n = 9, leaf_size = 10, bags = 150):
        self.verbose = verbose
        self.impact = impact
        #setting n attribute for creating indicators for training learner
        self.n = n   #using 9 because this is what i used for my manual strategy
        #initializing ML regressor as attribute and setting hyper-parameters
        self.learner = BagLearner(learner=RTLearner,
                                  kwargs={'leaf_size':leaf_size}, bags=bags)

    def author(self):
        return "rmiller327"

    def generate_indicators(self, prices):
        """
            helper method for generating features dataframe containing the
            training indicators

            input:
                prices:        dataframe containing the daily prices of a stock

            output:
                indicators_df: dataframe containing the Price/SMA Ratio,
                               Bollinger Bands, and Volatility of the daily
                               stock prices
        """
        #creating the indicator dfs
        price_sma_df = price_sma_ratio(prices, self.n)
        bb_df = bollinger_bands(prices, self.n)
        vol_df = volatility(prices, self.n)

        #creating features dataframe for training the regressor
        indicators_df = price_sma_df.join(bb_df,rsuffix="1").join(vol_df,rsuffix="2")
        indicators_df.columns = ["Price/SMA", "Bollinger Bands", "Volatility"]
        return indicators_df

    def preprocess_data(self, symbol, sd, ed):
        """
            helper method for reading in and preprocessing the prices data

            inputs:
                symbol: string representing the stock symbol for trading
                sd:     datetime object representing the date to start trading
                ed:     datetime object representing the date to stop trading

            output:
                prices: dataframe containing the preprocessed daily price data
                        for the given stock
        """
        #reading in the stock data using util.py and removing nulls
        dates = pd.date_range(sd, ed)
        prices = ut.get_data([symbol], dates)
        prices.drop(['SPY'], axis=1, inplace=True) #dropping SPY column
        prices.fillna(method='ffill', inplace=True) #forward-filling missing prices
        prices.fillna(method='bfill', inplace=True) #back-filling missing prices
        return prices

    def generate_orders_df(self, trades_df, symbol):
        """
            helper method for creating the order dataframe needed to run the
            market simulator

            input:
                trades_df: dataframe containing a trade (int) for each
                           trading day between sd and ed

            output:
                orders_df: dataframe containing the order type, date, number of
                           shares traded, and the stock symbol being traded for
                           each trade in trades_df
        """
        orders_df = trades_df.copy()
        orders_df.loc[orders_df[symbol] > 0 ,'Order'] = 'BUY'
        orders_df.loc[orders_df[symbol] < 0 ,'Order'] = 'SELL'
        orders_df.loc[orders_df[symbol] == 0 ,'Order'] = 'HOLD'
        orders_df['Date'] = orders_df.index.values
        orders_df['Shares'] = abs(orders_df.iloc[:,0].values)
        orders_df['Symbol'] = symbol
        orders_df.drop([symbol],axis=1,inplace=True)
        return orders_df

    # this method should train a Random Forest Regressor for trading
    def addEvidence(self, symbol = "IBM", sd=dt.datetime(2008,1,1),
                    ed=dt.datetime(2009,1,1), sv = 10000):
        """
            method for training a Random Forest regressor for predicting the
            price of the given stock

            inputs:
                symbol: string representing the stock symbol to trade
                sd:     datetime object representing the date to start trading
                ed:     datetime object representing the date to stop trading
                sv:     integer representing the starting amount of money you
                        have to trade with
            output:
                None
        """
        #reading in the price data
        prices = self.preprocess_data(symbol, sd, ed)
        #generating indicator dataframe for predicting
        features_df = self.generate_indicators(prices).fillna(method='bfill')
        #training regressor to predict prices using the indicators in indicators.py
        self.learner.addEvidence(features_df.values, prices.values)

    # this method should use the existing policy and test it against new data
    def testPolicy(self, symbol = "IBM", sd = dt.datetime(2009,1,1),
                   ed = dt.datetime(2010,1,1), sv = 10000):
        """
            method for using the trained Random Forest regressor to create a
            dataframe of stock trades for the given time period and stock

            inputs:
                symbol:    string representing the stock symbol to trade
                sd:        datetime object representing the date to start trading
                ed:        datetime object representing the date to stop trading
                sv:        integer representing the starting amount of money you
                           have to trade with
            output:
                df_trades: pandas dataframe containing a trade (int) for each
                           trading day between sd and ed
        """
        #reading in the price data
        prices = self.preprocess_data(symbol, sd, ed)

        #generating indicator dataframe for predicting
        features_df = self.generate_indicators(prices)

        #predicting prices using Random Forest regressor
        prices_array = self.learner.query(features_df.values)
        self.prices_pred = pd.DataFrame(prices_array,index=prices.index.values, columns=[symbol])

        #initializing df_trades to all 0s
        trades_df = prices.copy()
        trades_df.iloc[:,0] = 0

        #looping through the trading days and buying/selling/holding based on
        #the next day's predicted stock price; keeping counter variable for
        #current holdings (current_holdings cannot exceed +/- 1000)
        current_holdings = 0
        #starting at trading day n because we cannot trade using backfilled data
        for i in range(self.n,trades_df.shape[0]-1):
            #buying/selling if price goes up/down, else holding
            if self.prices_pred.iloc[i+1,0] > self.prices_pred.iloc[i,0]*(1+self.impact):  #price goes up
                trades_df.iloc[i,0] = 1000 - current_holdings #buy as much as we can
                current_holdings = 1000 #setting to current holdings
            elif self.prices_pred.iloc[i+1,0] < self.prices_pred.iloc[i,0]*(1-self.impact):  #price goes down
                trades_df.iloc[i,0] = -1000 - current_holdings #sell as much as we can
                current_holdings = -1000  #setting to current holdings
        return trades_df


if __name__ == "__main__":
    #running experiment 1
    print()
    print("######################  Experiment 1  ######################")
    print()
    from experiment1 import *
    np.random.seed(12)
    experiment1()

    #running experiment 2
    print()
    print("######################  Experiment 2  ######################")
    print()
    from experiment2 import *
    np.random.seed(12)
    experiment2()
