#!/usr/bin/env python
# coding: utf-8

import pandas as pd
import numpy as np
from pyscipopt import *
import math as math
import json

def Optimization(data,sch_hist):
    df1 = pd.json_normalize(data)
    constraint_type=pd.json_normalize(
        data['scheduleData'], 
        record_path =['constraint_type'],errors='ignore')
    for o in data['scheduleData']['song_library']:
        if len(o["content_metadata"])==0:
            o["content_metadata"]=[{}]
            print(o["content_metadata"])
    song_lib=pd.json_normalize(data['scheduleData']['song_library'],
        record_path =['content_metadata'],meta=['content_id', 'content_name', 'content_duration','song_id',
           'schedule_header.schedule_id', 'schedule_header.schedule_date',
           'schedule_header.channel_id'],errors='ignore',record_prefix="")

    song_df=song_lib.iloc[:,:5]
    slot_df=pd.json_normalize(data['scheduleData']['schedule_header'], record_path =['schedule_detail'],errors='ignore')

    slot_df['total_content_duration_sec']=slot_df['total_content_duration_sec'].astype(int)
    slot_df['ad_duration_sec']=slot_df['ad_duration_sec'].astype(int)
    slot_df['promo_duration_sec']=slot_df['promo_duration_sec'].astype(int)
    slot_df['filler_duration_sec']=slot_df['filler_duration_sec'].astype(int)
    slot_df['total_content_duration_sec']=slot_df['total_content_duration_sec'].astype(int)
    song_df['content_id']=song_df['content_id'].astype(int)

    constraint=pd.json_normalize(data['scheduleData']['schedule_header']['constraint'])

    #working
    def d_l_converter(x):
        ac=[]
        for i in range(len(x)):
            try:
                ac.append(x[i]['clock_id'])

            except:
                continue
            #print(ac)
        return ac

    constraint['ac']=constraint['applicable_clocks'].apply(d_l_converter)

    constraint_details=pd.json_normalize(
        data['scheduleData']['schedule_header']['constraint'],  record_path =['constraint_detail','constraint_detail_value'],
        meta=['constraint_id','is_constraint_hard','hardness_value','is_constraint_anded',['constraint_details','constraint_type_id'],
              ['constraint_details','is_applicable_day_level'],['constraint_details','min'],['constraint_details','constraint_level'],['constraint_details','metadata_type_id'],
              ['constraint_details','max'],['constraint_details','exact']],
        errors='ignore')

    constraint_df=constraint_details.merge(constraint,left_on='constraint_id',right_on='constraint_id',how='left')

    song_df_unique=song_df[['content_id','content_duration']].drop_duplicates()
    if sch_hist!=0:
        pd.json_normalize(data['scheduleData'],
            record_path =['schedule_history'],meta=['schedule_header.schedule_id','schedule_header.schedule_date','schedule_header.channel_id'],
            errors='ignore')
        
        df_sched_hist=pd.json_normalize(
            data['schedule_history'], 
            record_path =['schedule_output'],meta=['schedule_id','channel_id','schedule_date','schedule_header.schedule_id','schedule_header.schedule_date','schedule_header.channel_id'],
            errors='ignore')
        df_sched_hist["days"]=pd.DatetimeIndex(df_sched_hist.schedule_date).day
        df_sched_hist = df_sched_hist.merge(slot_df[["clock_id","clock_start_time"]], on='clock_start_time', how='left')  
        date = list(df_sched_hist.days.unique())
        song_list = list(song_df_unique.content_id)
        slots=list(slot_df["clock_id"])
        w={}
        wt=1000
        for i in date:
            day=df_sched_hist[df_sched_hist["days"]==i]
            print(i)
            for j in slots:
                slot = day[day["clock_id"]==j]
                for k in song_list:
                    if k in list(slot.content_id):
                         w[i,j,k]=wt
                    else:
                        w[i,j,k]=0
            wt=wt-100
######################################phase-1#################################################################################
    m = Model("MusicScheduler")
    x = {}
    for i in slot_df.clock_id:
        for j in song_df_unique.content_id:

            x[i,j] = m.addVar(lb=0,ub=1,vtype='I', name="x(%s,%s)" % (i,j))
            #print(x[i,j])

    slot_dict = {}   #Break Dictionary
    keys = list(slot_df.clock_id)
    values = list(slot_df.total_content_duration_sec)
    for ind,val in enumerate(keys):
        slot_dict[val] = values[ind]
    #print(slot_dict)

    sng = {}
    keys = list(song_df_unique.content_id)
    values = list(song_df_unique.content_duration)
    for ind,val in enumerate(keys):
        sng[val] = values[ind]
    #print(sng)

    for i in slot_df.clock_id:
        #print(slot_dict[i])
        m.addCons(quicksum(sng[j]*x[i,j] for j in song_df_unique.content_id) <= slot_dict[i], "song should not exceed slot duration")
#####################################no-back-to-back########################################################################################
    def no_back_to_back(metadata_type_id):
        print(metadata_type_id)
        for i in slot_df.clock_id:
            all_vars= []
            for j in song_df['content_id'].unique():
                all_vars.append(x[(i,j)])
            const_var=[]
            for k in song_df[song_df['metadata_type']==metadata_type_id]['content_id'].unique():
                try:
                    const_var.append(x[i,k])
                except:
                    continue
            if len(const_var)>1:
                #print("const_var",const_var)
                m.addCons(sum(const_var)*2<=sum(all_vars))

    for index,rows in constraint_df.iterrows():
        if rows['constraint_details.constraint_type_id']==13:
            metadata_type_id=(rows['constraint_details.metadata_type_id'])
            no_back_to_back(metadata_type_id)
 #####################################################exact-con###############################################################   
    def exact_cons():
        for index,rows in constraint_df[(constraint_df['constraint_details.constraint_type_id']==12) & (constraint_df['constraint_details.exact']>0)].iterrows():
            print(rows)
            if rows['constraint_details.constraint_level']=='song':
                cons_sng=[]
                for clk_id in rows['ac']:
                    cons_sng=[]
                    cons_sng.append(x[clk_id,rows['content_id']])
                    if len(cons_sng)>1:
                        m.addCons(quicksum(cons_sng)==rows['constraint_details.exact'])
            if rows['constraint_details.constraint_level']=='metadata':
                for clk_id in rows['ac']:
                    cons_sng=[]
                    for song in song_df[song_df['metadata_id']==rows['metadata_id']]['content_id'].unique():
                        cons_sng.append(x[clk_id,song])
                    if len(cons_sng)>1:
                        m.addCons(quicksum(cons_sng)==rows['constraint_details.exact'])
#########################################min-cons###################################################################
    def min_constraints():
        for index,rows in constraint_df[(constraint_df['constraint_details.constraint_type_id']==9) & (constraint_df['constraint_details.min']>0)].iterrows():
                if rows['constraint_details.is_applicable_day_level']==False:
                    if rows['constraint_details.constraint_level']=='song':
                        for clk_id in rows['ac']:
                            cons_min_sng=[]
                            cons_min_sng.append(x[clk_id,rows['content_id']])

                            m.addCons(sum(cons_min_sng)>=rows['constraint_details.min'])
                    if rows['constraint_details.constraint_level']=='metadata':

                        for clk_id in rows['ac']:
                            cons_min_sng=[]
                            for song in song_df[song_df['metadata_id']==rows['metadata_id']]['content_id'].unique():
                                cons_min_sng.append(x[clk_id,song])
                            m.addCons(quicksum(cons_min_sng)>=rows['constraint_details.min'])
                if rows['constraint_details.is_applicable_day_level']==True:
                    if rows['constraint_details.constraint_level']=='metadata':
                        cons_min_sng=[]
                        for slot in slot_df['clock_id']:
                            for song in song_df[song_df['metadata_id']==rows['metadata_id']]['content_id'].unique():
                                cons_min_sng.append(x[slot,song]) 
                        if len(cons_min_sng)>1:
                            m.addCons(quicksum(cons_min_sng)>=rows['constraint_details.min'])
                    if rows['constraint_details.constraint_level']=='song':
                        cons_min_sng=[]
                        for slot in slot_df['clock_id']:
                            cons_min_sng.append(x[slot,rows['content_id']])
                            if len(cons_min_sng)>1:
                                m.addCons(quicksum(cons_min_sng)>=rows['constraint_details.min'])
 ##########################################max-con#########################################################################################
    def max_constraints():
        for index,rows in constraint_df[(constraint_df['constraint_details.constraint_type_id']==10) & (constraint_df['constraint_details.max']>0)].iterrows():
                if rows['constraint_details.is_applicable_day_level']==False:
                    if rows['constraint_details.constraint_level']=='song':
                        for clk_id in rows['ac']:
                            cons_max_sng=[]
                            cons_max_sng.append(x[clk_id,rows['content_id']])
                            #cons_max_sng.append(x[rows['constraint_details.clock_id'],rows['content_id']])
                            m.addCons(sum(cons_max_sng)<=rows['constraint_details.max'])
                    if rows['constraint_details.constraint_level']=='metadata':
                        for clk_id in rows['ac']:
                            cons_max_sng=[]
                            for song in song_df[song_df['metadata_id']==rows['metadata_id']]['content_id'].unique():
                                #cons_max_sng.append(x[clk_id,rows['content_id']])
                                cons_max_sng.append(x[clk_id,song])

                                #cons_max_sng.append(x[rows['constraint_details.clock_id'],song])

                            m.addCons(sum(cons_max_sng)<=rows['constraint_details.max'])
                if rows['constraint_details.is_applicable_day_level']==True:
                    if rows['constraint_details.constraint_level']=='metadata':
                        cons_max_sng=[]
                        for slot in slot_df['clock_id']:
                            for song in song_df[song_df['metadata_id']==rows['metadata_id']]['content_id'].unique():
                                cons_max_sng.append(x[slot,song])
                        if len(cons_max_sng)>1:
                            m.addCons(sum(cons_max_sng)<=rows['constraint_details.max'])
                    if rows['constraint_details.constraint_level']=='song':
                        cons_max_sng=[]
                        for slot in slot_df['clock_id']:
                            cons_max_sng.append(x[slot,rows['content_id']]) 


                        #cons_max_sng.append(x[rows['constraint_details.clock_id'],rows['content_id']])
                        if len(cons_max_sng)>1:
                            m.addCons(sum(cons_max_sng)<=rows['constraint_details.max'])
 ################################################range-con#############################################################################
    def range_constraints():
        for index,rows in constraint_df[(constraint_df['constraint_details.constraint_type_id']==11) & (constraint_df['constraint_details.min']>0) & (constraint_df['constraint_details.max']>0)].iterrows():
                if rows['constraint_details.is_applicable_day_level']==False:
                    if rows['constraint_details.constraint_level']=='song':
                        for clk_id in rows['ac']:
                            cons_sng=[]
                            cons_sng.append(x[clk_id,rows['content_id']])
                            if len(cons_sng)>1:
                                m.addCons(sum(cons_sng)>=rows['constraint_details.min'])
                                m.addCons(sum(cons_sng)<=rows['constraint_details.max'])
                    if rows['constraint_details.constraint_level']=='metadata':
                        for clk_id in rows['ac']:
                            cons_sng=[]

                            for song in song_df[song_df['metadata_id']==rows['metadata_id']]['content_id'].unique():
                                    cons_sng.append(x[clk_id,song])

                            if len(cons_sng)>1:
                                m.addCons(sum(cons_sng)>=rows['constraint_details.min'])
                                m.addCons(sum(cons_sng)<=rows['constraint_details.max'])

                if rows['constraint_details.is_applicable_day_level']==True:
                    if rows['constraint_details.constraint_level']=='song':
                        cons_sng=[]
                        for slot in slot_df['clock_id']:
                            cons_sng.append(x[slot,rows['content_id']])
                        if len(cons_sng)>1:
                            m.addCons(sum(cons_sng)>=rows['constraint_details.min'])
                            m.addCons(sum(cons_sng)<=rows['constraint_details.max'])
                    if rows['constraint_details.constraint_level']=='metadata':

                        for slot in slot_df['clock_id']:
                            cons_sng=[]
                            for song in song_df[song_df['metadata_id']==rows['metadata_id']]['content_id'].unique():
                                cons_sng.append(x[slot,song])
                        if len(cons_sng)>1:
                            m.addCons(sum(cons_sng)>=rows['constraint_details.min'])
                            m.addCons(sum(cons_sng)<=rows['constraint_details.max'])
####################################################inclusion####################################################################

    def inclusion():
        min_slot_fill=0.8
        for index,rows in constraint_df[(constraint_df['constraint_details.constraint_type_id']==7)].iterrows():
            if rows['constraint_details.is_applicable_day_level']==False:
                if rows['constraint_details.constraint_level']=='song':
                    cons_all_sng=[]
                    cons_all_sng_duration=0
                    for clk_id in rows['ac']:
                        cons_all_sng.append((x[clk_id,rows['content_id']])*sng[song])
                        cons_all_sng_duration=sng[song]+cons_all_sng_duration
                    if cons_all_sng_duration>min_slot_fill*slot_dict[clk_id]:
                        m.addCons(quicksum(cons_all_sng)>=min_slot_fill*slot_dict[clk_id])
                        m.addCons(quicksum(cons_all_sng)<=slot_dict[clk_id])
                    if cons_all_sng_duration<min_slot_fill*slot_dict[clk_id]:
                        m.addCons(quicksum(cons_all_sng)==cons_all_sng_duration)
                if rows['constraint_details.constraint_level']=='metadata':
                    cons_all_sng=[]
                    cons_all_sng_duration=0
                    for clk_id in rows['ac']:
                        for song in song_df[song_df['metadata_id']==rows['metadata_id']]['content_id'].unique():
                            cons_all_sng.append(x[clk_id,song]*sng[song])
                            cons_all_sng_duration=sng[song]+cons_all_sng_duration
                        #m.addCons(quicksum(cons_all_sng)<=slot_dict[clk_id])
                        if cons_all_sng_duration>min_slot_fill*slot_dict[clk_id]:
                            m.addCons(quicksum(cons_all_sng)>=min_slot_fill*slot_dict[clk_id])
                            m.addCons(quicksum(cons_all_sng)<=slot_dict[clk_id])
                        if cons_all_sng_duration<min_slot_fill*slot_dict[clk_id]:
                            m.addCons(quicksum(cons_all_sng)==cons_all_sng_duration)
            if rows['constraint_details.is_applicable_day_level']==True:
                if rows['constraint_details.constraint_level']=='metadata':
                    cons_all_sng=[]
                    for slot in slot_df['clock_id']:
                        for song in song_df[song_df['metadata_id']==rows['metadata_id']]['content_id'].unique():
                            cons_min_sng.append(x[slot,song])
                            ln=len(cons_all_sng)
                            if len(cons_all_sng)>1:
                                m.addCons(sum(cons_all_sng)==ln)
                if rows['constraint_details.constraint_level']=='song':
                    cons_all_sng=[]
                    cons_all_sng.append(x[rows['constraint_details.clock_id'],rows['content_id']])
                    ln=len(cons_all_sng)
                    if len(cons_all_sng)>1:
                        m.addCons(sum(cons_all_sng)==ln)
#######################################################exclusion##########################################################################
    def exclusion():
        for index,rows in constraint_df[(constraint_df['constraint_details.constraint_type_id']==8)].iterrows():
            if rows['constraint_details.is_applicable_day_level']==False:
                if rows['constraint_details.constraint_level']=='song':
                    for clk_id in rows['ac']:
                        cons_all_sng=[]
                        cons_all_sng.append(x[clk_id,rows['content_id']])

                        m.addCons(quicksum(cons_all_sng)==0)
                if rows['constraint_details.constraint_level']=='metadata':
                    for clk_id in rows['ac']:
                        cons_all_sng=[]
                        for song in song_df[song_df['metadata_id']==rows['metadata_id']]['content_id'].unique():
                            cons_all_sng.append(x[clk_id,song])
                        m.addCons(quicksum(cons_all_sng)==0)
            if rows['constraint_details.is_applicable_day_level']==True:
                if rows['constraint_details.constraint_level']=='metadata':
                    cons_all_sng=[]
                    for slot in slot_df['clock_id']:
                        for song in song_df[song_df['metadata_id']==rows['metadata_id']]['content_id'].unique():
                            cons_all_sng.append(x[slot,song])
                    if len(cons_all_sng)>1:
                        m.addCons(quicksum(cons_all_sng)==0)
                if rows['constraint_details.constraint_level']=='song':
                    cons_all_sng=[]
                    for slot in slot_df['clock_id']:
                        cons_all_sng.append(x[slot,rows['content_id']])

                    if len(cons_all_sng)>1:
                        m.addCons(quicksum(cons_all_sng)==0)
    #exact_cons()
    #min_constraints
    #max_constraints()
    #range_constraints()
    inclusion()
    exclusion()
    if sch_hist!=0:
        obj=[]
        for i in date:
            for (j,k) in x:
                obj.append(w[i,j,k]*x[j,k])
        m.setObjective(quicksum(obj), "minimize")
        m.setObjective(quicksum(sng[j]*x[i,j] for (i,j) in x), "maximize")
    else:
        m.setObjective(quicksum(sng[j]*x[i,j] for (i,j) in x), "maximize")
    m.optimize()
    m.getStatus()
    print("Optimal value:", m.getObjVal())
    for j in x:
        v = x[j]
        if m.getVal(v) > 0:
            print(v.name, "=", m.getVal(v))
    Output = {'Value':[], 
            'Content_id':[], 
            'Slot_id':[] 
           } 

    df = pd.DataFrame(Output) 

    for (i,j) in x:
        if m.getVal(x[i,j]) > 0:
            df.loc[len(df.index)] = [m.getVal(x[i,j]),j,i]
    df['position']=df.groupby(['Slot_id'])['Content_id'].cumcount()+1
    df_order=df
    m1 = Model("ordering")

    Output = {
            'Content_id':[],
            'Position':[], 
            'clock_id':[] 
           } 
    df_output = pd.DataFrame(Output) 

    def add_basic_constraint_1(k):
        for sng in df[df['Slot_id']==k]['Content_id']:
            active_spots1=[]
            for pos in df[df['Slot_id']==k]['position']:
                active_spots1.append(y[sng,pos])
            m1.addCons(quicksum(active_spots1) == 1)

    def add_basic_constraint_2(k):
        for pos in df[df['Slot_id']==k]['position']:
            active_spots2=[]
            for sng in df[df['Slot_id']==k]['Content_id']:
                active_spots2.append(y[sng,pos])
            m1.addCons(quicksum(active_spots2) == 1)

    def apply_no_back_to_back(k):
        if rows['constraint_details.constraint_type_id']==13:
            metadata_type_id=(rows['constraint_details.metadata_type_id'])
            print(metadata_type_id)
            const_var=[]
            constraint_applicable_sng = []
            constraint_applicable_sng=set(song_df[song_df['metadata_type']==metadata_type_id]['content_id'].unique()).intersection(df_order[df_order['Slot_id']==k]['Content_id'])
            if len(constraint_applicable_sng)>1:
                print(p,k)
                print("constraint_applicable_sng",constraint_applicable_sng)
                picked_sng_combi=[]
                for p_1 in constraint_applicable_sng:
                    for p_2  in constraint_applicable_sng:
                        if (p_1 != p_2) & (tuple((p_2,p_1)) not in set(picked_sng_combi)):
                            picked_sng_combi.append(tuple((p_1,p_2)))

                for i_sng_tuple in picked_sng_combi:
                    constraint_applicable_sng_positions_1=[]
                    constraint_applicable_sng_positions_2=list()
                    for pos_i_1 in range(1, len(df_order[df_order['Slot_id']==k])+1):
                        constraint_applicable_sng_position_1 = y[i_sng_tuple[0], pos_i_1]
                        constraint_applicable_sng_positions_1.append(constraint_applicable_sng_position_1*pos_i_1)
                        constraint_applicable_sng_position_2 = y[i_sng_tuple[1], pos_i_1]
                        constraint_applicable_sng_positions_2.append(constraint_applicable_sng_position_2*pos_i_1)

                    m1.addCons(abs(quicksum(constraint_applicable_sng_positions_1) - quicksum(constraint_applicable_sng_positions_2)) >= 2)

    k=0
    for k in slot_df.clock_id:
        m1 = Model("ordering")
        y = {}

        for i in df.Content_id:
            for j in df.position:
                y[i,j] = m1.addVar(lb=0,ub=1,vtype='I', name="y(%s,%s)" % (i,j))
        #Basic-1 No repeat of song
        add_basic_constraint_1(k)

        #Basic-1 No repeat of Position
        add_basic_constraint_2(k)
        apply_no_back_to_back(k)

        m1.optimize()

        for (i,j) in y:
            if m1.getVal(y[i,j]) > 0:
                print(i,j)
                df_output.loc[len(df_output.index)] = [i,j,k]

    df_output.sort_values(['clock_id','Position'], ascending=[True,True], inplace=True)
    df_output['Content_id'] = df_output['Content_id'].apply(lambda f: format(f, '.0f'))
    df_output['Position'] = df_output['Position'].apply(lambda f: format(f, '.0f'))
    df_output['clock_id'] = df_output['clock_id'].apply(lambda f: format(f, '.0f'))

    df_output = df_output.round()
    df_dict=df_output.to_dict(orient='index')
    df_vals=list(df_dict.values())
    output={}
    output["schedule_id"]=data['scheduleData']['schedule_header']["schedule_id"]
    output["schedule_date"] = data['scheduleData']['schedule_header']["schedule_date"]
    output["channel_id"] = data['scheduleData']['schedule_header']["channel_id"]
    output["schedule_output"]=df_vals
    with open('output.json', 'w') as f:
        json.dump(output, f)
    return output
    

