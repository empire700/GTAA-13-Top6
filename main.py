'''An implementation of Meb Faber's AGGRESSIVE model: Global Tactical Asset Allocation model GTAA(13) ranking
stocks on 1/3/6/12month MOM and owning TOP6 with 10-month SimpleMovingAverage Filter (200day), monthly rebalance: 
https://papers.ssrn.com/sol3/papers.cfm?abstract_id=962461
"A Quantitative Approach to Tactical Asset Allocation" published May 2006.
Analysis only occurs at month End/Start, signals are NOT generated intra-month.
'''
# self.Debug(str(dir( x )))
from alpha_model import MomentumAndSMAAlphaModel

class GlobalTacticalAssetAllocation(QCAlgorithm):
    
    def Initialize(self):
        
        #self.SetStartDate(date(2014, 1, 29) + timedelta(days=200)) 
        self.SetStartDate(2014, 5, 20)
        self.SetEndDate(2020, 5, 20)
        self.SetCash(100000) 
        self.Settings.FreePortfolioValuePercentage = 0.02
        self.SetBrokerageModel(BrokerageName.InteractiveBrokersBrokerage, AccountType.Margin)

        self.UniverseSettings.Resolution = Resolution.Daily
        tickerWeightPairs = { # (1x) ETF EarliestStartDate: 2014/02
                                'VLUE': 0.05,     # 5% US Large Value, (VLUE, 2013/05)
                                'MTUM': 0.05,     # 5% US Large Momentum (MTUM, 2013/5)
                                'VBR': 0.05,      # 5% US Small Cap Value (VBR)
                                'XSMO': 0.05,     # 5% US Small Cap Momentum (XSMO) 
                                'EFA': 0.10,      # 10% Foreign Developed (EFA)
                                'VWO': 0.10,      # 10% Foreign Emerging (VWO)
                                'IEF': 0.05,      # 5% US 10Y Gov Bonds (IEF)
                                'TLT': 0.05,      # 5% US 30Y Gov Bonds (TLT)
                                'LQD': 0.05,      # 5% US Corporate Bonds (LQD)
                                'BWX': 0.05,      # 5% Foreign 10Y Gov Bonds (BWX)
                                'DBC': 0.10,      # 10% Commodities (DBC)
                                'GLD': 0.10,      # 10% Gold (GLD)
                                'VNQ': 0.20       # 20% NAREIT (VNQ)
                                }
                                
        symbols = [Symbol.Create(ticker, SecurityType.Equity, Market.USA) 
                for ticker in [*tickerWeightPairs]]
        self.AddUniverseSelection( ManualUniverseSelectionModel(symbols) )
        
        weightsTotal = sum(tickerWeightPairs.values())
        if weightsTotal != 1.0:
            self.Log(f"********** Weights = {str(weightsTotal)}. WILL be scaled down to 1.0   **********  ")
        
        self.AddAlpha( MomentumAndSMAAlphaModel( tickerWeightPairs = tickerWeightPairs) )
        self.Settings.RebalancePortfolioOnSecurityChanges = False
        self.Settings.RebalancePortfolioOnInsightChanges = False
        self.SetPortfolioConstruction( InsightWeightingPortfolioConstructionModel(self.RebalanceFunction,\
                                                                                    PortfolioBias.Long) )
        self.SetExecution( ImmediateExecutionModel() ) 
        self.AddRiskManagement( NullRiskManagementModel() )
        self.Log("GTAA(13) Initialsing... ")
        self.lastRebalanceTime = None
        
    def RebalanceFunction(self, time):
        # initial rebalance
        if self.lastRebalanceTime == None:
            self.lastRebalanceTime = time
            return Expiry.EndOfDay(self.Time)
            
        # Recurrent Rebalance time
        self.Log("GTAA(13) PortfolioConstruction Rebalancing... ")
        return Expiry.EndOfMonth(self.Time)