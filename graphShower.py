import os
from itunesLibrary import library
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


if __name__ == '__main__':
	if os.path.isfile('/Users/alex/AppsMine/AnilistScraper/historyStats.csv'):
		df = pd.read_csv('/Users/alex/AppsMine/AnilistScraper/historyStats.csv')

	selectedNames = ["OneGles", "Piede", "Suzuju"]
	df = df.loc[df['name'].isin(selectedNames)]
	lastDay = df.columns[-1]
	df = df.sort_values(by=[lastDay], ascending=False)
	df = df.replace(-1, np.nan)
	print(df)
	df = df.set_index('name')
	df = df.transpose()
	print(df)
	df.plot(legend=True)
	
	#plt.figure(figsize=(20,12))
	plt.xlabel('x - giorno')
	# Set the y axis label of the current axis.
	plt.ylabel('y - ep visti')
	# Set a title of the current axes.
	plt.title('Ep visti - Rizzi & Pera ')
	# show a legend on the plot
	# Display a figure
	#plt.show()
	path = "charts/result.png"

	fig = plt.gcf()
	#fig.set_size_inches(18.5, 18.5)
	#fig.savefig(path, dpi=200)
	plt.show()