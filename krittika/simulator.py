import os
import statistics

from scalesim.topology_utils import topologies
from scalesim.scale_config import scale_config
from scalesim.compute.operand_matrix import operand_matrix
from krittika.config.krittika_config import KrittikaConfig
from krittika.partition_manager import PartitionManager
from krittika.single_layer_sim import SingleLayerSim


class Simulator:
    def __init__(self):
        # Objects
        self.config_obj = KrittikaConfig()
        self.partition_obj = PartitionManager()
        self.workload_obj = topologies()

        # State
        self.verbose = True
        self.trace_gen_flag = True
        self.autopartition = False
        self.single_layer_objects_list = []
        self.top_path='./'
        self.reports_dir_path = './'

        # REPORT Structures
        # self.total_cycles_report_grid = []
        # self.stall_cycles_report_grid = []
        # self.overall_utils_report_grid = []
        # self.mapping_eff_report_grid = []
        self.cycles_report_avg_items = []
        self.bandwidth_report_avg_items = []

        # Flags
        self.all_layer_run_done = False
        self.params_valid = False
        self.runs_done = False
        self.reports_dir_ready = False
        

    def set_params(self,
                   config_filename='',
                   workload_filename='',
                   custom_partition_filename='',
                   reports_dir_path='./',
                   verbose=True,
                   save_traces=True
                   ):
        # Read the user input and files and prepare the objects
        self.config_obj.read_config_from_file(filename=config_filename)

        self.workload_obj = topologies()
        self.workload_obj.load_arrays(topofile=workload_filename)

        self.partition_obj.set_params(config_obj=self.config_obj,
                                      workload_obj=self.workload_obj
                                      )
        self.autopartition = self.config_obj.is_autopartition()
        if self.autopartition:
            self.partition_obj.create_partition_table()
        else:
            self.partition_obj.read_user_partition_table(filename=custom_partition_filename)

        self.verbose = verbose
        self.trace_gen_flag = save_traces

        self.reports_dir_path = reports_dir_path

        self.params_valid = True

    #
    def run(self):
        # Orchestrate among the function calls to run simulations
        assert self.params_valid, 'Cannot run simulation without inputs'

        # Run compute simulations for all layers first
        num_layers = self.workload_obj.get_num_layers()

        # Update the offsets to generate operand matrices
        single_arr_config = scale_config()
        conf_list = scale_config.get_default_conf_as_list()
        user_offsets = self.config_obj.get_operand_offsets()
        conf_list[6] = user_offsets[0]
        conf_list[7] = user_offsets[1]
        conf_list[8] = user_offsets[2]

        # print("################################### \n", conf_list, "\n ############################# \n")

        single_arr_config.update_from_list(conf_list=conf_list)

        for layer_id in range(num_layers):
            if self.verbose:
                print('Running Layer ' + str(layer_id))
            this_layer_op_mat_obj = operand_matrix()

            this_layer_op_mat_obj.set_params(config_obj=single_arr_config,
                                             topoutil_obj=self.workload_obj,
                                             layer_id=layer_id)

            this_layer_sim = SingleLayerSim()
            this_layer_sim.set_params(config_obj=self.config_obj,
                                      op_mat_obj=this_layer_op_mat_obj,
                                      partitioner_obj=self.partition_obj,
                                      layer_id=layer_id,
                                      log_top_path=self.top_path,
                                      verbosity=self.verbose)
            this_layer_sim.run()
            self.single_layer_objects_list += [this_layer_sim]

            if self.save_traces:
                if self.verbose:
                    print('SAVING TRACES')
                this_layer_sim.save_traces()

        self.all_layer_run_done = True
        self.runs_done = True
        self.generate_all_reports()

    # Report generation

    def generate_all_reports(self):
        assert self.all_layer_run_done, 'Layer runs are not done yet'
        
        self.create_cycles_report_structures()
        self.create_bandwidth_report_structures()

        compute_report_name = self.top_path + '/results/COMPUTE_REPORT_4_cores_test.csv'
        compute_report = open(compute_report_name, 'w')
        header = 'LayerID, Total Cycles, Stall Cycles, Overall Util %, Mapping Efficiency %, Compute Util %,\n'
        compute_report.write(header)

        bandwidth_report_name = self.top_path + '/results/BANDWIDTH_REPORT_4_cores_test.csv'
        bandwidth_report = open(bandwidth_report_name, 'w')
        header = 'LayerID, Avg IFMAP SRAM BW, Avg FILTER SRAM BW, Avg OFMAP SRAM BW, '
        header += 'Avg IFMAP DRAM BW, Avg FILTER DRAM BW, Avg OFMAP DRAM BW,\n'
        bandwidth_report.write(header)

        # detail_report_name = self.top_path + '/DETAILED_ACCESS_REPORT.csv'
        # detail_report = open(detail_report_name, 'w')
        # header = 'LayerID, '
        # header += 'SRAM IFMAP Start Cycle, SRAM IFMAP Stop Cycle, SRAM IFMAP Reads, '
        # header += 'SRAM Filter Start Cycle, SRAM Filter Stop Cycle, SRAM Filter Reads, '
        # header += 'SRAM OFMAP Start Cycle, SRAM OFMAP Stop Cycle, SRAM OFMAP Writes, '
        # header += 'DRAM IFMAP Start Cycle, DRAM IFMAP Stop Cycle, DRAM IFMAP Reads, '
        # header += 'DRAM Filter Start Cycle, DRAM Filter Stop Cycle, DRAM Filter Reads, '
        # header += 'DRAM OFMAP Start Cycle, DRAM OFMAP Stop Cycle, DRAM OFMAP Writes,\n'
        # detail_report.write(header)

        for lid in range(self.workload_obj.get_num_layers()):
            # single_layer_obj = self.single_layer_objects_list[lid]
            compute_report_items_this_layer = self.cycles_report_avg_items
            log = str(lid) +', '
            log += ', '.join([str(x) for x in compute_report_items_this_layer])
            log += ',\n'
            compute_report.write(log)

            bandwidth_report_items_this_layer = self.bandwidth_report_avg_items
            log = str(lid) + ', '
            log += ', '.join([str(x) for x in bandwidth_report_items_this_layer])
            log += ',\n'
            bandwidth_report.write(log)

            # detail_report_items_this_layer = single_layer_obj.get_detail_report_items()
            # log = str(lid) + ', '
            # log += ', '.join([str(x) for x in detail_report_items_this_layer])
            # log += ',\n'
            # detail_report.write(log)

        compute_report.close()
        bandwidth_report.close()
        # detail_report.close()

    def create_cycles_report_structures(self):
        assert self.runs_done

        for lid in range(self.workload_obj.get_num_layers()):
            this_layer_sim_obj = self.single_layer_objects_list[lid]

            total_cycles_list = this_layer_sim_obj.get_total_cycles_list()
            stall_cycles_list = this_layer_sim_obj.get_stall_cycles_list()
            overall_util_list = this_layer_sim_obj.get_overall_util_list()
            mapping_eff_list = this_layer_sim_obj.get_mapping_eff_list()
            compute_util_list = this_layer_sim_obj.get_compute_util_list()

            self.cycles_report_avg_items += [statistics.mean(total_cycles_list)]
            self.cycles_report_avg_items += [statistics.mean(stall_cycles_list)]
            self.cycles_report_avg_items += [statistics.mean(overall_util_list)]
            self.cycles_report_avg_items += [statistics.mean(mapping_eff_list)]
            self.cycles_report_avg_items += [statistics.mean(compute_util_list)]


    def create_bandwidth_report_structures(self):
        assert self.runs_done

        for lid in range(self.workload_obj.get_num_layers()):
            this_layer_sim_obj = self.single_layer_objects_list[lid]

            avg_ifmap_sram_bw_list = this_layer_sim_obj.get_avg_ifmap_sram_bw_list()
            avg_filter_sram_bw_list = this_layer_sim_obj.get_avg_filter_sram_bw_list()
            avg_ofmap_sram_bw_list = this_layer_sim_obj.get_avg_ofmap_sram_bw_list()

            avg_ifmap_dram_bw_list = this_layer_sim_obj.get_avg_ifmap_dram_bw_list()
            avg_filter_dram_bw_list = this_layer_sim_obj.get_avg_filter_dram_bw_list()
            avg_ofmap_dram_bw_list = this_layer_sim_obj.get_avg_ofmap_dram_bw_list()

            self.bandwidth_report_avg_items += [statistics.mean(avg_ifmap_sram_bw_list)]
            self.bandwidth_report_avg_items += [statistics.mean(avg_filter_sram_bw_list)]
            self.bandwidth_report_avg_items += [statistics.mean(avg_ofmap_sram_bw_list)]
            self.bandwidth_report_avg_items += [statistics.mean(avg_ifmap_dram_bw_list)]
            self.bandwidth_report_avg_items += [statistics.mean(avg_filter_dram_bw_list)]
            self.bandwidth_report_avg_items += [statistics.mean(avg_ofmap_dram_bw_list)]

    # def create_detailed_report_structures(self):
    #     print('WIP')

    # def save_all_cycle_reports(self):
    #     print('WIP')

    # def save_all_bw_reports(self):
    #     print('WIP')

    # def save_all_detailed_reports(self):
    #     print('WIP')

    # def save_traces(self):
    #     print('WIP')


