from es_utils import get_indexes, open_index, delete_index

if __name__ == "__main__":
    dxs = get_indexes()
    print dxs
    '''
    with open('opened.txt','r') as opened:
	lines = opened.readlines()
	for line in lines:
            source_index = line.strip('\n')
	    dest_index = source_index.replace('_testindex','')
            print source_index, dest_index
            reindex_with_new_name(source_index, dest_index)
    
    with open('all_test.txt','r') as opened:
        lines = opened.readlines()
        for line in lines:
            source_index = line.strip('\n')
            #dest_index = source_index.replace('_testindex','')
            #print source_index, dest_index
            #delete_index(source_index)
            #reindex_with_new_name(source_index,dest_index)    
            #close_index(source_index)
    ''' 
    #name = 'cmssdt-externals_stats_summary_testindex-2656'
    #alias = 'cmssdt-externals_stats_summary-2656'
    #name = 'cmssdt-externals_stats_summary_testindex-2652'
    #alias = 'cmssdt-externals_stats_summary-2652'
    #get_aliases_for_index(name)
    #reindex_with_new_name(name, alias)
    #delete_alias(name, alias)
