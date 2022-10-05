from MenloLoader import *


class Analyser():

    def __init__(self):
        self.ml = MenloLoader([])
        self.files = []
        self.dfDict = {}
        self.referenceDF = None


    def convDF(self, df):
        
        res = pd.DataFrame()
        df.drop(['freq', 'FFT'], axis = 1, inplace = True)
        for i in range(len(df)):
            time  = df.loc[i]['time']
            amp = df.loc[i]['amp']

            res = pd.concat([res, self.ml.get_FD(time,amp)], axis = 0).reset_index(drop = True)
        
        df = pd.concat([res, df], axis = 1) 
        return df


    def correctPhase(self, df):
        
        """Correct low frequency phase error"""

        for i in range(len(df)):
            phase_offset_index = self.ml.find_nearest(df.loc[i]['p_freq'], 0.2)[0]
            df.at[i, 'pd'] = df.loc[i]['pd'] - df.loc[i]['pd'][phase_offset_index]
        return df


    def get_samples(self, df_m, df_r):

        """Calculate quantities for sample against reference and return the result dataframe"""

        p_d, tr, c_tr, = [[] for i in range(3)]

        for j in range(len(df_m)):
            p_d.append(df_m.loc[j]['phase'] - df_r.loc[j]['phase'])
            tr.append(df_m.loc[j]['FFT']/ df_r.loc[j]['FFT'])
            c_tr.append(df_m.loc[j]['c_FFT']/ df_r.loc[j]['c_FFT'])
        df_m['pd'] = p_d
        df_m['TR'] = tr
        df_m['c_tr'] = c_tr
        df_m = self.ml.unwrp_phase(df_m,'pd')
        df_m = self.correctPhase(df_m)
        return df_m