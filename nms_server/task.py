# The class Task for the server is responsable for:
# - Storing and obtaining the tasks for each agent based on the configuration file.
# - Parsing and calling the database functions to store the metrics received.
class Task:
    def __init__(self, config):
        self.config = config
        self.tasks = dict()
        # Create the dictionary to store the tasks for each agent
        for task in self.config['tasks']:
            if task['agent_id'] not in self.tasks:
                self.tasks[task['agent_id']] = []
            self.tasks[task['agent_id']].append(task)

        # for agent_id, tasks in self.tasks.items():
        #     print(f"Agent ID: {agent_id}")
        #     for task in tasks:
        #         print(f"Task: {task}")

    def get_agent_tasks(self, agent_id):
        try:
            return self.tasks[agent_id]
        except KeyError:
            return None
