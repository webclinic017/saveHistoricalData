import os.path
import datetime
import sqlite3

import backtrader as bt
import backtrader.indicators as btind
import pandas as pd

"""
Custom indicator - VWAP
"""
class VolumeWeightedAveragePrice(bt.Indicator):
    plotinfo = dict(subplot=False)

    params = (('period', 30), )

    alias = ('VWAP', 'VolumeWeightedAveragePrice','vwap')
    lines = ('VWAP',)
    plotlines = dict(VWAP=dict(alpha=0.50, linestyle='-.', linewidth=2.0))



    def __init__(self):
        # Before super to ensure mixins (right-hand side in subclassing)
        # can see the assignment operation and operate on the line
        cumvol = bt.ind.SumN(self.data.volume, period = self.p.period)
        typprice = ((self.data.close + self.data.high + self.data.low)/3) * self.data.volume
        cumtypprice = bt.ind.SumN(typprice, period=self.p.period)
        self.lines[0] = cumtypprice / cumvol

        super(VolumeWeightedAveragePrice, self).__init__()

"""
Basic test strategy 
"""
class testStrategy(bt.Strategy):
    params = (
        ('smaperiod', 20),
        ('printlog', False),
        ('vwapperiod', 12)
    )
    
    def log(self, txt, dt=None, doprint=True):
        ''' Logging function for this strategy'''
        if self.params.printlog or doprint:
            dt = dt or self.datas[0].datetime.date(0)
            print('%s, %s' % (dt.isoformat(), txt))
    
    def __init__(self):
        ## keep a reference to the close price in the data[0] dataseries
        self.dataclose = self.datas[0].close

        ## to keep track of pending orders
        self.order = None
        self.buyprice = None
        self.buycomm = None

        ## Add a MovingAverageSimple indicator
        self.sma = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=self.params.smaperiod)
        
        self.sma_fast = bt.indicators.SimpleMovingAverage(
            self.datas[0], period=5)

        self.vwap = VolumeWeightedAveragePrice(
           self.datas[0], period = self.params.vwapperiod)

        ## Indicators for the plotting show
        
        #bt.indicators.ExponentialMovingAverage(self.datas[0], period=25)
        #bt.indicators.WeightedMovingAverage(self.datas[0], period=25,
        #                                    subplot=True)
        #bt.indicators.StochasticSlow(self.datas[0])
        #bt.indicators.MACDHisto(self.datas[0])
        rsi = bt.indicators.RSI(self.datas[0])
        #bt.indicators.SmoothedMovingAverage(rsi, period=10)
        #bt.indicators.ATR(self.datas[0], plot=False)

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            # Buy/Sell order submitted/accepted to/by broker - Nothing to do
            return

        # Check if an order has been completed
        # Attention: broker could reject order if not enough cash
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    'BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                    (order.executed.price,
                     order.executed.value,
                     order.executed.comm))

                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:  # Sell
                self.log('SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price,
                          order.executed.value,
                          order.executed.comm))

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
                 (trade.pnl, trade.pnlcomm))

    def next(self):
        # log the closing price
        #self.log('Close, %.2f, VWAP: %.2f'%(self.dataclose[0], self.vwap[0]))

        # Check if an order is pending ... if yes, we cannot send a 2nd one
        if self.order:
            return

        # Check if we are in the market
        if not self.position:

        ##### Not yet ... we MIGHT BUY if ...
            if self.sma[0] > self.vwap[0]:
                    
                    if self.sma[-1] > self.vwap[-1]:
                        # previous close more than the previous sma
                        
                        # BUY with default parameters
                        self.log('BUY Open, %.2f' % self.dataclose[0])

                        # Keep track of the created order to avoid a 2nd order
                        self.order = self.buy()
                        #input('press key...')

        else:

            # Already in the market ... we might sell
            #if len(self) >= (self.bar_executed + 5):
            if (self.sma[0] > self.sma_fast[0]):
                if (self.sma[-1] > self.sma_fast[-1]):
                    #if (self.sma[-2] > self.sma_fast[-2]):
                    # SELL with all possible default parameters
                    self.log('SELL Open, %.2f' % self.dataclose[0])

                    # Keep track of the created order to avoid a 2nd order
                    self.order = self.sell()

    def stop(self):
        self.log('(MA Period %2d) Ending Value %.2f'%(self.params.smaperiod, self.broker.getvalue()), doprint=True)


"""
SMA based strategy
"""
class SMA_CrossOver(bt.Strategy):

    params = (('fast', 10), ('slow', 30))

    def __init__(self):

        sma_fast = btind.SMA(period=self.p.fast)
        sma_slow = btind.SMA(period=self.p.slow)

        self.buysig = btind.CrossOver(sma_fast, sma_slow)

    def next(self):
        if self.position.size:
            if self.buysig < 0:
                self.sell()

        elif self.buysig > 0:
            self.buy()

"""
Function to load date from CSV 

Params
---------
csvFilePath: [str] filepath to csv file containing history 

"""
def getHistory_CSV(csvFilePath):
    #modpath = os.path.dirname(os.path.abspath(sys.argv[0]))
    csvFilePath = 'SOXL_OneHour.csv'

    # Create a Data Feed
    data = bt.feeds.GenericCSVData(
        dataname=csvFilePath,
        nullvalue=0.0,

        dtformat=('%Y-%m-%d'),
        tmformat=('%H:%M:%S'),

        datetime=0,
        time=1,
        high=4,
        low=3,
        open=5,
        close=6,
        volume=7,
        openinterest=-1,
        reverse=True,
        header=True)
    
    return data

"""
Function to load date from CSV 

Params
---------
csvFilePath: [str] filepath to csv file containing history 

"""
def getHistory_SQL(dbFilePath, symbol, interval):
    #modpath = os.path.dirname(os.path.abspath(sys.argv[0]))
    #csvFilePath = 'SOXL_OneHour.csv'
    
    conn = sqlite3.connect(dbFilePath)
    tableName = symbol+'_'+'stock'+'_'+interval
    sqlStatement = 'SELECT * FROM ' + tableName
    symbolHistory = pd.read_sql(sqlStatement, conn)
    
    symbolHistory['start'] = symbolHistory['start'].astype(str).str[:-7]
    symbolHistory.drop(['end'], axis=1, inplace=True)
    symbolHistory['start'] = pd.to_datetime(symbolHistory['start'])
    symbolHistory.set_index('start', inplace=True)
    print(symbolHistory.head())

    data = bt.feeds.PandasData(dataname=symbolHistory)
    
    
    
    # Create a Data Feed
    """
    data = bt.feeds.GenericCSVData(
        dataname=dbFilePath,
        nullvalue=0.0,

        dtformat=('%Y-%m-%d'),
        tmformat=('%H:%M:%S'),

        datetime=0,
        time=1,
        high=4,
        low=3,
        open=5,
        close=6,
        volume=7,
        openinterest=-1,
        reverse=True,
        header=True)
    """
    return data

## initialize the cerebro engine 
cr = bt.Cerebro()

# Add the Data Feed to Cerebro
cr.adddata(getHistory_SQL('historicalData.db', 'AAPL', 'OneHour'))

## add a strategy
cr.addstrategy(testStrategy)
#strats = cr.optstrategy(
#    testStrategy,
#    maperiod=range(10, 30))

## set cash 
cr.broker.setcash(2000)

# Add a FixedSize sizer according to the stake
cr.addsizer(bt.sizers.FixedSize, stake=2)

# Set the commission - 0.1% ... divide by 100 to remove the %
cr.broker.setcommission(commission=0.01)

print('Starting Portfolio Value: %.2f' % cr.broker.getvalue())

cr.run(maxcpus=1)

print('Final Portfolio Value: %.2f' % cr.broker.getvalue())

cr.plot()