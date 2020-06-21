class MomentumAndSMAAlphaModel(AlphaModel):
    ''' Alpha model(Original): Price > SMA own asset, else own RiskOff (IEF). 
        AggressiveModel: EqualWeight top6 ranked by average 1,3,6,12month momentum, if Price > SMA. Else RiskOff.
    '''

    def __init__(self, tickerWeightPairs, rebalancingPeriod = Expiry.EndOfMonth, smaLength=200, resolution=Resolution.Daily):
        '''Initializes a new instance of the SmaAlphaModel class
        Args:
            period: The SMA period
            resolution: The reolution for the SMA'''
        self.tickerWeightPairs = tickerWeightPairs
        self.rebalancingPeriod = rebalancingPeriod
        self.smaLength = smaLength
        self.resolution = resolution
        self.symbolDataBySymbol = {}
        self.month = -1
        self.riskOffAsset = "IEF"

    def Update(self, algorithm, data):
        '''This is called each time the algorithm receives data for (@resolution of) subscribed securities
        Returns: The new insights generated.
        THIS: analysis only occurs at month start, so any signals intra-month are disregarded.'''
        if self.month == algorithm.Time.month:
            return []
        self.month = algorithm.Time.month
        

        insights = []
        riskOffWeight = riskOnWeight = 1 / len(self.tickerWeightPairs)
        
        positiveMomentumSecurities = list(filter(lambda x: x.MomentumScore > 0, self.symbolDataBySymbol))
        for symbol, symbolData in self.symbolDataBySymbol.items():
            
            price = algorithm.Securities[symbol].Price

            if price != 0 and symbolData.MovingAverage.IsReady:

                if price > symbolData.MovingAverage.Current.Value:
                    insights.append( Insight.Price(symbol, Expiry.EndOfMonth, InsightDirection.Up,  None, None, None, riskOnWeight))

                elif price < symbolData.MovingAverage.Current.Value:
                    insights.append( Insight.Price(symbol, Expiry.EndOfMonth, InsightDirection.Flat,  None, None, None, 0) )
                    riskOffWeight += riskOnWeight
                    
        insights.append( Insight.Price(self.riskOffAsset, Expiry.EndOfMonth, InsightDirection.Up,  None, None, None, riskOffWeight) )
        return insights


        def OnSecuritiesChanged(self, algorithm, changes):
        
            for added in changes.AddedSecurities:
                weight = self.tickerWeightPairs[str(added)]
                self.symbolDataBySymbol[added.Symbol] = SymbolData(added, weight, algorithm, self.smaLength, self.resolution)
    
            for removed in changes.RemovedSecurities:
                symbolData = self.symbolDataBySymbol.pop(removed.Symbol, None)
                if symbolData:
                    # Remove consolidator
                    symbolData.dispose()          


class SymbolData:
    
    def __init__(self, security, weight, algorithm, smaLength, resolution):
        self.Security = security
        self.Symbol = security.Symbol
        self.Weight = weight
        self.MovingAverage = SimpleMovingAverage(smaLength)
        self.MOMPOne = MomentumPercent(21)
        self.MOMPThree = MomentumPercent(63)
        self.MOMPSix = MomentumPercent(126)
        self.MOMPTwelve = MomentumPercent(252)
        self.MomentumScore = None
        self.algorithm = algorithm

        # Warm up MA
        history = algorithm.History([self.Symbol], 253, resolution).loc[self.Symbol]
        for time, row in history.iterrows():
#TODO: Check moving average to only most recent 200days.
            self.MovingAverage.Update(time, row["close"])
            self.MOMPOne.Update(time, row["close"])
            
            
        # Setup indicator consolidator
        self.consolidator = TradeBarConsolidator(timedelta(1))
        self.consolidator.DataConsolidated += self.CustomDailyHandler
        algorithm.SubscriptionManager.AddConsolidator(self.Symbol, self.consolidator)
        
        CalculateMomentumScore()
        
    def CustomDailyHandler(self, sender, consolidated):
# TODO: Check moving average is only most recent 200days.
        self.MovingAverage.Update(consolidated.Time, consolidated.Close)
        self.MOMPOne.Update(consolidated.Time, consolidated.Close)
        self.MomentumScore = self.MOMPOne*12
        
    def dispose(self):
        self.algorithm.SubscriptionManager.RemoveConsolidator(self.Symbol, self.consolidator)
    
    def IndicatorsAreReady(self):
        
        if self.MovingAverage.IsReady and self.MOMPOne.IsReady:
            return True
        
        return False
    
    def CalculateMomentumScore(self, history):
        
        ''' Calculate the weighted average momentum value for each security '''
        
        returnSeries = history.loc[self.Symbol]['close'].pct_change(periods = 1).dropna() # 1-day returns for last year
        
        cumRet1 = (returnSeries.tail(21).add(1).prod()) - 1 # 1-month momentum
        cumRet3 = (returnSeries.tail(63).add(1).prod()) - 1 # 3-month momentum
        cumRet6 = (returnSeries.tail(126).add(1).prod()) - 1 # 6-month momentum
        cumRet12 = (returnSeries.tail(252).add(1).prod()) - 1 # 12-month momentum
        
        self.momentumScore = (cumRet1 * 12 + cumRet3 * 4 + cumRet6 * 2 + cumRet12) # weighted average momentum