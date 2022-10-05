
import pandas as pd
import csv
import numpy as np
import datetime
from scipy import signal as sgnl
from sklearn.linear_model import LinearRegression
import os

class MenloLoader:

    def __init__(self, src_flist, config = None):

        self.src_flist = src_flist
        self.win = 400
        self.config = config
        #self.src_flist, self.src_TDS, self.dtlist = self.File_Loader_Menlo(self.src_flist)
        self.src_TDS, self.dtlist = self.FileLoader(self.src_flist)
        self.data = self.get_data2(self.src_flist, self.src_TDS, self.dtlist)
        FD = pd.DataFrame()
        for i in range(len(self.data)):
            FD = pd.concat([FD,self.get_FD(self.data.loc[i]['time'],
                                            self.data.loc[i]['amp'])],
                                            axis = 0).reset_index(drop = True)
        self.data = pd.concat([FD, self.data], axis = 1) 

  
    def find_nearest(self,array, value):  

        array = np.asarray(array)
        idx = (np.abs(array - value)).argmin()
        return idx, array[idx] 

        
    def unwrp_phase(self,df,key):
        """Performs phase unwrapping on the values of a specified key in given dataframe.
        
            *Arguments*
    
            df : Dataframe object
            key: key to the data e.g. 'phase' or phase difference 'pd'. This series 
                        must have the same length as the array with key 'p_freq'.

            *Returns*

            df: Dataframe object with unwrapped phase
        """
        freq_lst = []
        phase_lst = []
        for i in range(len(df)) :
            phase = df.loc[i]['%s'%key]
            p_freq = df.loc[i]['p_freq']
            for k in range(1):
                for m in range(1,len(phase)):
                    diff = phase[m] - phase[m-1]
                    if diff > np.pi:
                        phase[m:] = phase[m:] - 2*np.pi
                    elif diff < -np.pi:
                        phase[m:] = phase[m:] + 2*np.pi                        
            x0 = self.find_nearest(p_freq,0.1)
            x1 = self.find_nearest(p_freq,0.3)
            ex_freq = p_freq[x0[0]:x1[0]].reshape((-1,1))
            ex_phase = phase[x0[0]:x1[0]]
            model = LinearRegression().fit(ex_freq,ex_phase)
            #r_sq = model.score(ex_freq,ex_phase)
            offset = model.intercept_
            phase = phase[x0[0]:] - offset
            p_freq = p_freq[x0[0]:] 
            freq_lst.append(p_freq)
            phase_lst.append(phase)
        df['%s'%key] = phase_lst
        df['p_freq'] = freq_lst
        return df  


    def get_FD(self,time, TDS_signal): 

        c_FFT = []
        # Pad zeros on the time signal to reach this length
        t_ser_len = 16384
        phase = []
        e_time = time
        e_amp = TDS_signal
        T = e_time[1]-e_time[0]                      
        e_time = e_time - time[0]
        N0 = len(e_time)
        # e_time = e_time[:(self.find_nearest(e_time, self.win)[0])]                   
        # e_amp = e_amp[:(self.find_nearest(e_time, self.win)[0])]
        N = len(e_time)              
        w = sgnl.tukey(N, alpha = 0.1) 

        e_amp = w*(e_amp)                                     
           
        pad = t_ser_len - N  
        e_time = np.append(e_time, np.zeros(pad))          
        e_amp = np.append(e_amp, np.zeros(pad))
        N0 = len(e_time)

        freq = np.fft.fftfreq(N0, T)
        zero_THz_idx = self.find_nearest(freq, 0)[0]
        freq= freq[zero_THz_idx:int(len(freq)/2)]
        e_FFT = np.fft.fft(e_amp)/(N0/2)   
        e_FFT = e_FFT[zero_THz_idx:int(len(e_FFT)/2)]     
        FFT = np.abs(e_FFT)
        
        for j in range(len(e_FFT)):
            phase.append(np.arctan2(e_FFT[j].imag,e_FFT[j].real))
        phase = np.array(phase)
        start = self.find_nearest(freq,0.2)[0]
        stop = self.find_nearest(freq,2)[0]
        slc_freq = freq[start:stop]
        phase = phase[start:stop]
        slc_FFT = FFT[start:stop]                        
        p_freq = slc_freq
        phase = phase
        c_FFT.append({'freq':freq,
                        'FFT': FFT, 'c_FFT': e_FFT,
                        'p_freq' : p_freq ,
                        'phase' : phase,'slc_FFT' : slc_FFT})
        c_FFT = pd.DataFrame(c_FFT)
        return c_FFT
            
    def getDatetime2(self, filesrclist, dtlist):   
        """
        Loops through list of files, fetches the DateTime indices for the
        measurement and stores it in a list.

        *Arguments*

        filesrclist : list containing strings containing file paths.
        dtlist : Destination list to store DateTime values for files referenced 
                in filesrclist.

        *Returns*

        dtlist : list containing the retrieved DateTime values from the files 
                referenced in filesrclist.
        """  
        for j in range(len(filesrclist)):
            with open(filesrclist[j]) as dtr: 
                for com in dtr:
                    if com.startswith('#') and "Timestamp" in com:
                        dtlist.append(datetime.datetime.\
                                        strptime(com.split('Timestamp')[1]\
                                                .split('\n')[0][2:],
                                                "%Y-%m-%dT%H:%M:%S"))                 
        return dtlist


    def get_data(self, src_flist, src_TDS, dtlist):

        for i in range(len(src_flist)):
            name = src_flist[i].split("\\")[-1].split(".")[0]
            attrs = name.split("_")
            if "Reference" in name:
                Type = "Reference"
                sensor_id = attrs[4]
            src_TDS[i]['sensor_id'] = sensor_id
            src_TDS[i]['Type'] = Type
            src_TDS[i]['Datetime'] = dtlist[i]
        data = pd.DataFrame(src_TDS)
        return data

    def get_data2(self, src_flist, src_TDS, dtlist):

        for i in range(len(src_flist)):
            name = src_flist[i].split("\\")[-1].split(".")[0]
            chip = name.split("_")[0]
            angle = name.split("_")[1]

            src_TDS[i]['design'] = chip[:-2]
            src_TDS[i]['sensor_id'] = chip[-1:]
            src_TDS[i]['angle'] = angle
            src_TDS[i]['Datetime'] = dtlist[i]
        data = pd.DataFrame(src_TDS)
        return data

    def FileLoader(self, src_flist):

        src_TDS = []
        dtlist = []
        #Look for TDS files and save paths to arrays
        src_TDS = self.getTDS(src_flist, src_TDS)
        dtlist = self.getDatetime(src_flist, dtlist)
        return src_TDS, dtlist    

            
    def File_Loader_Menlo(self, local_path, win = 400, norm_freq = 0):

        src_flist = []
        src_TDS = []
        dtlist = []
        path = local_path

        #Look for TDS files and save paths to arrays

        for i, (dirpath, dirnames, filenames) in enumerate(os.walk(path)):
            for a in filenames:
                filename = os.path.join(dirpath, a)
                if ('fft' not in filename and 'README' not in filename and '.yml' not in filename and '.txt' in filename):
                    src_flist.append(filename)
    #         src_flist = self.data_selector(src_flist,meta,target)
        src_TDS = self.getTDS(src_flist, src_TDS)
        dtlist = self.getDatetime2(src_flist, dtlist)
        return src_flist, src_TDS, dtlist    


    def getTDS(self,src_flist, des_TDS):   

        for j in range(len(src_flist)):
            e_time = []
            e_amp = []
            with open(src_flist[j]) as csvfile: 
                reader = csv.reader(csvfile, delimiter ='\t')
                for k in range(5): next(reader)
                for row in reader:
                    e_time.append(float(row[0]))
                    e_amp.append(float(row[1]))           
                e_time = np.array(e_time) - e_time[0]        
                des_TDS.append({'time':np.array(e_time), 'amp':np.array(e_amp)})
        return des_TDS
    

    def getDatetime(self, filesrclist, dtlist):    

        for j in range(len(filesrclist)):
            with open(filesrclist[j]) as dtr: 
                for com in dtr:
                    if com.startswith('#') and "Timestamp" in com and 'wafer' not in com:
                        dtlist.append(
                                      datetime.datetime.strptime(com.split('Timestamp')[1]\
                                                                 .split('\n')[0][2:],
                                                                '%y-%m-%dT%H:%M:%S'))                   
                    elif com.startswith('#') and "Timestamp" in com and 'wafer' in com:
                        try:
                            dtlist.append(
                                          datetime.datetime.strptime(com.split('Timestamp')[1].split(',')[0] \
                                                                 .split('\n')[0][2:][2:],
                                                                '%y-%m-%dT%H:%M:%S'))                   
                        except ValueError:                                                            
                            print("Incorrect file type")

        return dtlist

    
