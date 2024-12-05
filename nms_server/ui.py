import json

import sql.database as db


class UI:
    def __init__(self, server_hostname, pool, verbose=False):
        self.running = True
        self.view_mode = False  # Real-time view mode
        self.server_hostname = server_hostname
        self.pool = pool
        self.verbose = verbose

    def display_title(self):
        print("========================================")
        print("    Network Management System Server    ")
        print("========================================")

    def save_status(self, message):
        db.operation.insert(db.values.log_type.STATUS, self.server_hostname, message)
        if self.view_mode:
            print(f"[STATUS] ({self.server_hostname}) {message}")

    def save_alert(self, hostname, alert_type, message):
        db.operation.insert(db.values.log_type.ALERT,  hostname, message)
        if self.view_mode:
            print(f"[ALERT]  ({hostname}) {{{alert_type}}} {message}")

    def save_metrics(self, hostname, metrics):
        db.operation.insert_metrics(hostname, metrics)
        if self.view_mode:
            print(f"[METRIC] ({hostname}) Metric received. Task ID: {metrics.get('task_id')}")

    def display_info(self, message):
        print(f"[INFO] {message}")

    def display_error(self, message):
        print(f"[ERROR] {message}")

    def display_warning(self, message):
        print(f"[WARNING] {message}")

    def display_tasks(self, tasks):
        print("[CONFIG] Loaded Tasks:")
        print(json.dumps(tasks, indent=2))

    def display_menu(self):
        print()
        print("Menu")
        print("1. Display Loaded Tasks")
        print("2. View Real-Time Events")
        print("3. View Connected Agents")
        print("4. Shutdown Server")

    def handle_menu_choice(self, choice, tcp_server, udp_server, config):
        match choice:
            case 1:
                self.display_tasks(config["tasks"])
            case 2:
                self.display_info("Listening for real-time connections, alerts and metrics...\n"
                                  "Press Enter to return to the main menu.")
                self.view_mode = True
                input()
                self.view_mode = False
            case 3:
                agents = self.pool.get_connected_clients()
                n = len(agents)
                if n == 0:
                    print("No agents connected.")
                else:
                    print(f"{len(agents)} Connected Agents:")
                    for agent in agents:
                        print(f"Agent: {agent}")
                        if self.verbose:
                            print(f"Address: {agents[agent]}")
                            print(f"Sequence Number: {self.pool.get_seq_number(agent)}")
                            print(f"Packets to Ack: {self.pool.packets_to_ack[agent]}")
                            print(f"Packets to Reorder: {self.pool.packets_to_reorder[agent]}")
                            print(f"Window Size: {self.pool.agents_window_sizes[agent]}")
            case 4:
                self.display_info("Shutting down server...")
                self.running = False
            case _:
                self.display_error("Invalid choice. Please try again.")

    def main_menu(self, tcp_server, udp_server, config):
        while self.running:
            self.display_menu()
            try:
                choice = int(input("Enter your choice: "))
                self.handle_menu_choice(choice, tcp_server, udp_server, config)
            except ValueError:
                self.display_error("Invalid input. Please enter a number.")
