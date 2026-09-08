// Arial custom ECharts build: gauge + bar + line, tooltip/grid, SVG renderer only.
import * as echarts from "echarts/core";
import { GaugeChart, BarChart, LineChart } from "echarts/charts";
import { TooltipComponent, GridComponent } from "echarts/components";
import { SVGRenderer } from "echarts/renderers";
echarts.use([GaugeChart, BarChart, LineChart, TooltipComponent, GridComponent, SVGRenderer]);
window.echarts = echarts;
