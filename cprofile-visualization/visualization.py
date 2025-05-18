import pstats
import matplotlib.pyplot as plt
import numpy as np


def create_flame_chart(profile_file, output_file=None, min_percentage=0.01,
                       fig_width=12, fig_height=8, colormap='viridis'):
    """
    Create a flame chart from a cProfile .profile file

    Args:
        profile_file (str): Path to the .profile file
        output_file (str, optional): File to save the chart to
        min_percentage (float, optional): Minimum percentage of total time to include in chart
        fig_width (float, optional): Width of the figure in inches
        fig_height (float, optional): Height of the figure in inches
        colormap (str, optional): Matplotlib colormap to use
    """
    # Load the profile data
    stats = pstats.Stats(profile_file)

    # Get function stats
    function_stats = []
    total_time = 0

    for func, (cc, nc, tt, ct, callers) in stats.stats.items():
        file_path, line_number, function_name = func
        if '/<' in function_name:  # Skip dynamically created functions
            continue

        module_name = file_path.split('/')[-1].replace('.py', '')
        full_name = f"{module_name}.{function_name}"

        # Store stats
        function_stats.append({
            'name': full_name,
            'cumulative_time': ct,
            'total_time': tt,
            'calls': nc,
            'callers': callers
        })
        total_time += tt

    # Sort by cumulative time
    function_stats.sort(key=lambda x: x['cumulative_time'], reverse=True)

    # Filter functions that take less than min_percentage of total time
    min_time = total_time * min_percentage
    function_stats = [f for f in function_stats if f['total_time'] > min_time]

    # Create a mapping of functions to their callers
    call_hierarchy = {}
    for func in function_stats:
        callers_data = {}
        for caller, (cc, nc, tt, ct) in func['callers'].items():
            if caller in stats.stats:
                caller_file, caller_line, caller_func = caller
                caller_module = caller_file.split('/')[-1].replace('.py', '')
                caller_name = f"{caller_module}.{caller_func}"
                callers_data[caller_name] = ct
        call_hierarchy[func['name']] = callers_data

    # Set up the plot
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))

    # Create the flame chart
    cmap = plt.get_cmap(colormap)
    colors = cmap(np.linspace(0, 1, len(function_stats)))

    y_pos = 0
    y_positions = {}
    bar_height = 0.8
    stack_levels = {}
    max_depth = 0

    # First pass: determine stack levels
    def determine_stack_level(func_name, level=0, visited=None):
        if visited is None:
            visited = set()

        if func_name in visited:
            return level

        visited.add(func_name)
        max_level = level

        # Look at callers of this function
        callers = call_hierarchy.get(func_name, {})
        for caller in callers:
            caller_level = determine_stack_level(caller, level + 1, visited.copy())
            max_level = max(max_level, caller_level)

        stack_levels[func_name] = max_level
        return max_level

    # Determine stack levels for all functions
    for func in function_stats:
        level = determine_stack_level(func['name'])
        max_depth = max(max_depth, level)

    # Second pass: plot bars
    sorted_funcs = sorted(function_stats, key=lambda x: stack_levels.get(x['name'], 0))

    for i, func in enumerate(sorted_funcs):
        name = func['name']
        level = stack_levels.get(name, 0)

        # Calculate x position and width based on cumulative time
        start_x = 0
        width = func['cumulative_time']

        # Plot bar
        ax.barh(y_pos, width, height=bar_height, left=start_x,
                color=colors[i % len(colors)], alpha=0.7,
                edgecolor='white', linewidth=0.5)

        # Add text label if bar is wide enough
        if width > total_time * 0.05:
            time_percent = func['total_time'] / total_time * 100
            cumul_percent = func['cumulative_time'] / total_time * 100
            label = f"{name} ({time_percent:.1f}%, cum: {cumul_percent:.1f}%)"
            ax.text(start_x + width/2, y_pos, label,
                    ha='center', va='center', color='black',
                    fontsize=8, fontweight='bold')

        y_positions[name] = y_pos
        y_pos += 1

    # Set plot labels and title
    ax.set_xlabel('Time (seconds)')
    ax.set_ylabel('Function')
    ax.set_title(f'Flame Chart - {profile_file}')

    # Set y-ticks
    function_names = [func['name'] for func in sorted_funcs]
    ax.set_yticks(list(range(len(function_names))))
    ax.set_yticklabels(function_names, fontsize=8)

    # Display grid lines
    ax.grid(axis='x', linestyle='--', alpha=0.7)

    # Tight layout
    plt.tight_layout()

    # Save to file if requested
    if output_file:
        plt.savefig(output_file, dpi=300, bbox_inches='tight')

    # Display the plot
    plt.show()

    return fig, ax


if __name__ == "__main__":
    # Replace 'your_profile.profile' with the path to your .profile file
    create_flame_chart('data/report.profile',
                      output_file='flame_chart.png',
                      min_percentage=0.01,
                      fig_width=15,
                      fig_height=10)
