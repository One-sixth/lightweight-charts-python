import { generateCandleData } from '../sample-data';
import { Handler } from '../general/handler';

// Handler 构造函数签名: (chartId, innerWidth, innerHeight, nrows, ncols, index, autoSize, paneIndex?, marker_auto_scale?)
const handler = new Handler("sadasdas", 0.556, 0.5182, 1, 1, 1, true);

handler.createToolBox();

const data = generateCandleData();
if (handler.series)
handler.series.setData(data);
