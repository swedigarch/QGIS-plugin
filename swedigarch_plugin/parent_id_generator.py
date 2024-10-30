import time
import pandas as pd
from qgis.core import QgsTask, QgsApplication
from PyQt5.QtCore import pyqtSignal, QObject, QEventLoop

class ResultContainer(QObject):
    result_ready = pyqtSignal(pd.DataFrame)
    all_tasks_finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.result = None
        self.completed_tasks = 0
        self.total_tasks = 0

    def fibonacci(self, n):
        if n <= 1:
            return n
        return self.fibonacci(n-1) + self.fibonacci(n-2)

    def task_finished(self):
        self.completed_tasks += 1
        if self.completed_tasks == self.total_tasks:
            self.all_tasks_finished.emit()

class DataFrameTask(QgsTask):
    def __init__(self, dataframe, result_container):
        super().__init__("DataFrame Calculation Task", QgsTask.CanCancel)
        self.dataframe = dataframe
        self.result_container = result_container
        self.result = None
    
    def run(self):
        try:
            # Utför beräkningar på DataFrame (ingen interaktion med QGIS-objekt)
            num_rows = self.dataframe.shape[0]
            #for i in range(num_rows):
            #    time.sleep(0.000001)
            #self.result = self.dataframe.apply(lambda x: x * 2)  # Exempelberäkning
            self.result = self.dataframe.apply(self.fibonacci)
            return True
        except Exception as e:
            self.error_message = str(e)
            return False

    def finished(self, result):
        if result:
            # Lagra resultatet i result_container och emit signal
            self.result_container.result = self.result
            self.result_container.result_ready.emit(self.result)
        else:
            print(f"Task failed with error: {self.error_message}")
        # Signalera att denna task är klar
        self.result_container.task_finished()

# Slot-funktion för att hantera resultatet när signalen emittas
def handle_result(result):
    print("Result (first rows):")
    print(result.head())

# Funktion för att dela upp DataFrame i flera delar och skapa tasks
def split_dataframe_and_run_tasks(dataframe, num_tasks):
    result_container = ResultContainer()
    #result_container.result_ready.connect(handle_result)
    result_container.total_tasks = num_tasks

    # Dela upp DataFrame i lika stora delar
    chunk_size = len(dataframe) // num_tasks
    tasks = []
    for i in range(num_tasks):
        start_row = i * chunk_size
        end_row = (i + 1) * chunk_size if i != num_tasks - 1 else len(dataframe)
        chunk = dataframe.iloc[start_row:end_row]
        task = DataFrameTask(chunk, result_container)
        tasks.append(task)
        QgsApplication.taskManager().addTask(task)

    # Vänta på att alla tasks ska slutföras
    loop = QEventLoop()
    result_container.all_tasks_finished.connect(loop.quit)
    loop.exec_()

    return result_container.result

# Exempel på användning
data = {'A': range(1, 30), 'B': range(1, 30)}
df = pd.DataFrame(data)

# Mät tid för flera tasks
num_tasks = 1
start_time = time.time()
result = split_dataframe_and_run_tasks(df, num_tasks)
multiple_tasks_time = time.time() - start_time
print(f"Förbrukad tid för {num_tasks} tasks: {multiple_tasks_time} sekunder")

print("Resultat:")
print(result.head())
