import { useState, useEffect } from 'react';
import { Button } from './components/ui/button';
import { Badge } from './components/ui/badge';
import { Separator } from './components/ui/separator';
import { Input } from './components/ui/input';
import { Label } from './components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './components/ui/select';
import { Switch } from './components/ui/switch';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from './components/ui/table';
import { 
  Camera, 
  Settings, 
  Database, 
  FileText, 
  ClipboardList,
  User,
  Monitor,
  Play,
  Minus,
  Maximize2,
  X,
  Video,
  VideoOff,
  Link,
  Unlink,
  Check,
  Wifi,
  Clock,
  Image as ImageIcon,
  Film,
  FolderOpen,
  Server,
  Cpu,
  Brain,
  Box,
  Package,
  Download,
  Upload,
  Trash2,
  Eye,
  CheckCircle,
  XCircle,
  AlertCircle,
  Calendar,
  Search,
  Filter
} from 'lucide-react';

type ContentView = 'camera' | 'system' | 'model' | 'process' | 'records';

interface UserInfo {
  workstation: string;
  employeeId: string;
  name: string;
}

interface DesktopAppProps {
  userInfo: UserInfo;
  onGoToTasks?: () => void;
}

export default function DesktopApp({ userInfo, onGoToTasks }: DesktopAppProps) {
  const [activeContent, setActiveContent] = useState<ContentView>('camera');
  const [currentTime, setCurrentTime] = useState(new Date());
  const [isCameraConnected, setIsCameraConnected] = useState(false);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [exposureTime, setExposureTime] = useState(5000);
  const [gain, setGain] = useState(1.0);
  const [frameCount, setFrameCount] = useState(0);
  
  // 系统设置状态
  const [serverAddress, setServerAddress] = useState('192.168.1.100');
  const [serverPort, setServerPort] = useState('8080');
  const [imageSavePath, setImageSavePath] = useState('C:\\VisionData\\Images');
  const [imageRetentionDays, setImageRetentionDays] = useState('30');
  const [logSavePath, setLogSavePath] = useState('C:\\VisionData\\Logs');
  const [logRetentionDays, setLogRetentionDays] = useState('90');

  // 更新时间
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  // 模拟帧计数
  useEffect(() => {
    if (isPreviewing) {
      const interval = setInterval(() => {
        setFrameCount(prev => prev + 1);
      }, 33); // ~30fps
      return () => clearInterval(interval);
    }
  }, [isPreviewing]);

  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('zh-CN', { 
      hour: '2-digit', 
      minute: '2-digit', 
      second: '2-digit',
      hour12: false 
    });
  };

  const formatDate = (date: Date) => {
    return date.toLocaleDateString('zh-CN', { 
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    });
  };

  const handleConnectCamera = () => {
    setIsCameraConnected(true);
  };

  const handleDisconnectCamera = () => {
    setIsCameraConnected(false);
    setIsPreviewing(false);
  };

  const handleStartPreview = () => {
    if (isCameraConnected) {
      setIsPreviewing(true);
    }
  };

  const handleStopPreview = () => {
    setIsPreviewing(false);
  };

  const handleApplySettings = () => {
    console.log('应用相机设置', { exposureTime, gain });
  };

  return (
    <div className="dark bg-[#1a1a1a] flex items-center justify-center min-h-screen p-4">
      {/* 16:9 容器 */}
      <div 
        className="w-full bg-[#1a1a1a] border border-[#3a3a3a] overflow-hidden shadow-2xl"
        style={{ maxWidth: '1920px', aspectRatio: '16/9' }}
      >
        <div className="h-full flex flex-col">
          
          {/* 顶部标题栏 */}
          <header className="bg-[#252525] border-b border-[#3a3a3a] px-6 py-3 flex-shrink-0">
            <div className="flex items-center justify-between">
              
              {/* 左侧 - Logo */}
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded bg-orange-500 flex items-center justify-center">
                  <Monitor className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h1 className="text-white">ProcVision</h1>
                  <p className="text-gray-400 text-xs">Industrial Vision Management System</p>
                </div>
              </div>

              {/* 右侧 - 用户信息和窗口控制 */}
              <div className="flex items-center gap-6">
                {/* 工位信息 */}
                <div className="flex items-center gap-2">
                  <Monitor className="w-4 h-4 text-orange-500" />
                  <div>
                    <div className="text-gray-400 text-xs">工位</div>
                    <div className="text-white text-sm">{userInfo.workstation}</div>
                  </div>
                </div>

                <Separator orientation="vertical" className="h-10 bg-[#3a3a3a]" />

                {/* 用户信息 */}
                <div className="flex items-center gap-2">
                  <User className="w-4 h-4 text-orange-500" />
                  <div>
                    <div className="text-gray-400 text-xs">操作员</div>
                    <div className="text-white text-sm">{userInfo.employeeId} / {userInfo.name}</div>
                  </div>
                </div>

                <Separator orientation="vertical" className="h-10 bg-[#3a3a3a]" />

                {/* 当前时间 */}
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-orange-500" />
                  <div>
                    <div className="text-gray-400 text-xs">{formatDate(currentTime)}</div>
                    <div className="text-white text-sm">{formatTime(currentTime)}</div>
                  </div>
                </div>

                <Separator orientation="vertical" className="h-10 bg-[#3a3a3a]" />

                {/* 窗口控制按钮 */}
                <div className="flex items-center gap-2">
                  {onGoToTasks && (
                    <Button
                      onClick={onGoToTasks}
                      className="bg-orange-500 hover:bg-orange-600 text-white h-8 w-8 p-0"
                    >
                      <Play className="w-3 h-3" />
                    </Button>
                  )}
                  <Button
                    variant="outline"
                    className="bg-transparent text-gray-400 border-[#3a3a3a] hover:bg-gray-800 hover:text-white w-8 h-8 p-0"
                  >
                    <Minus className="w-4 h-4" />
                  </Button>
                  <Button
                    variant="outline"
                    className="bg-transparent text-gray-400 border-[#3a3a3a] hover:bg-gray-800 hover:text-white w-8 h-8 p-0"
                  >
                    <Maximize2 className="w-4 h-4" />
                  </Button>
                  <Button
                    variant="outline"
                    className="bg-transparent text-red-400 border-[#3a3a3a] hover:bg-red-500/10 hover:border-red-500 w-8 h-8 p-0"
                  >
                    <X className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            </div>
          </header>

          {/* 主内容区 */}
          <div className="flex-1 flex overflow-hidden">
            
            {/* 左侧导航面板 */}
            <aside className="w-72 bg-[#1f1f1f] border-r border-[#3a3a3a] flex flex-col">
              
              {/* 功能菜单 */}
              <div className="flex-1 p-4 overflow-y-auto">
                <div className="space-y-2 mb-6">
                  <Button
                    onClick={() => setActiveContent('camera')}
                    className={`w-full justify-start h-auto py-3 px-4 ${
                      activeContent === 'camera'
                        ? 'bg-orange-500 text-white hover:bg-orange-600'
                        : 'bg-transparent text-gray-400 hover:bg-[#252525] hover:text-white'
                    }`}
                  >
                    <Camera className="w-5 h-5 mr-3 flex-shrink-0" />
                    <div className="flex-1 text-left">
                      <div className={activeContent === 'camera' ? 'text-white' : 'text-gray-300'}>相机设置</div>
                      <div className={`text-xs ${activeContent === 'camera' ? 'text-orange-100' : 'text-gray-500'}`}>
                        Camera Settings
                      </div>
                    </div>
                  </Button>

                  <Button
                    onClick={() => setActiveContent('system')}
                    className={`w-full justify-start h-auto py-3 px-4 ${
                      activeContent === 'system'
                        ? 'bg-orange-500 text-white hover:bg-orange-600'
                        : 'bg-transparent text-gray-400 hover:bg-[#252525] hover:text-white'
                    }`}
                  >
                    <Settings className="w-5 h-5 mr-3 flex-shrink-0" />
                    <div className="flex-1 text-left">
                      <div className={activeContent === 'system' ? 'text-white' : 'text-gray-300'}>系统设置</div>
                      <div className={`text-xs ${activeContent === 'system' ? 'text-orange-100' : 'text-gray-500'}`}>
                        System Settings
                      </div>
                    </div>
                  </Button>

                  <Button
                    onClick={() => setActiveContent('model')}
                    className={`w-full justify-start h-auto py-3 px-4 ${
                      activeContent === 'model'
                        ? 'bg-orange-500 text-white hover:bg-orange-600'
                        : 'bg-transparent text-gray-400 hover:bg-[#252525] hover:text-white'
                    }`}
                  >
                    <Database className="w-5 h-5 mr-3 flex-shrink-0" />
                    <div className="flex-1 text-left">
                      <div className={activeContent === 'model' ? 'text-white' : 'text-gray-300'}>模型管理</div>
                      <div className={`text-xs ${activeContent === 'model' ? 'text-orange-100' : 'text-gray-500'}`}>
                        Model Management
                      </div>
                    </div>
                  </Button>

                  <Button
                    onClick={() => setActiveContent('process')}
                    className={`w-full justify-start h-auto py-3 px-4 ${
                      activeContent === 'process'
                        ? 'bg-orange-500 text-white hover:bg-orange-600'
                        : 'bg-transparent text-gray-400 hover:bg-[#252525] hover:text-white'
                    }`}
                  >
                    <FileText className="w-5 h-5 mr-3 flex-shrink-0" />
                    <div className="flex-1 text-left">
                      <div className={activeContent === 'process' ? 'text-white' : 'text-gray-300'}>工艺信息</div>
                      <div className={`text-xs ${activeContent === 'process' ? 'text-orange-100' : 'text-gray-500'}`}>
                        Process Information
                      </div>
                    </div>
                  </Button>

                  <Button
                    onClick={() => setActiveContent('records')}
                    className={`w-full justify-start h-auto py-3 px-4 ${
                      activeContent === 'records'
                        ? 'bg-orange-500 text-white hover:bg-orange-600'
                        : 'bg-transparent text-gray-400 hover:bg-[#252525] hover:text-white'
                    }`}
                  >
                    <ClipboardList className="w-5 h-5 mr-3 flex-shrink-0" />
                    <div className="flex-1 text-left">
                      <div className={activeContent === 'records' ? 'text-white' : 'text-gray-300'}>工作记录</div>
                      <div className={`text-xs ${activeContent === 'records' ? 'text-orange-100' : 'text-gray-500'}`}>
                        Work Records
                      </div>
                    </div>
                  </Button>
                </div>
              </div>

              {/* 底部状态 */}
              <div className="p-4 border-t border-[#3a3a3a] bg-[#1a1a1a]">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Wifi className="w-4 h-4 text-green-500" />
                    <span className="text-green-400 text-sm">Connected</span>
                  </div>
                  <div className="text-gray-500 text-xs">v3.2.1</div>
                </div>
                <div className="text-gray-500 text-xs">
                  Last sync: {formatTime(currentTime)}
                </div>
              </div>
            </aside>

            {/* 右侧内容区 */}
            <div className="flex-1 flex flex-col overflow-hidden bg-[#1a1a1a]">
              
              {activeContent === 'camera' ? (
                <CameraSettingsPanel
                  isCameraConnected={isCameraConnected}
                  isPreviewing={isPreviewing}
                  exposureTime={exposureTime}
                  gain={gain}
                  frameCount={frameCount}
                  onConnect={handleConnectCamera}
                  onDisconnect={handleDisconnectCamera}
                  onStartPreview={handleStartPreview}
                  onStopPreview={handleStopPreview}
                  onExposureChange={setExposureTime}
                  onGainChange={setGain}
                  onApplySettings={handleApplySettings}
                />
              ) : activeContent === 'system' ? (
                <SystemSettingsPanel
                  serverAddress={serverAddress}
                  serverPort={serverPort}
                  imageSavePath={imageSavePath}
                  imageRetentionDays={imageRetentionDays}
                  logSavePath={logSavePath}
                  logRetentionDays={logRetentionDays}
                  onServerAddressChange={setServerAddress}
                  onServerPortChange={setServerPort}
                  onImageSavePathChange={setImageSavePath}
                  onImageRetentionDaysChange={setImageRetentionDays}
                  onLogSavePathChange={setLogSavePath}
                  onLogRetentionDaysChange={setLogRetentionDays}
                />
              ) : activeContent === 'model' ? (
                <ModelManagementPanel />
              ) : activeContent === 'process' ? (
                <ProcessInfoPanel />
              ) : activeContent === 'records' ? (
                <WorkRecordsPanel />
              ) : null}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}

// 相机设置面板组件
interface CameraSettingsPanelProps {
  isCameraConnected: boolean;
  isPreviewing: boolean;
  exposureTime: number;
  gain: number;
  frameCount: number;
  onConnect: () => void;
  onDisconnect: () => void;
  onStartPreview: () => void;
  onStopPreview: () => void;
  onExposureChange: (value: number) => void;
  onGainChange: (value: number) => void;
  onApplySettings: () => void;
}

function CameraSettingsPanel({
  isCameraConnected,
  isPreviewing,
  exposureTime,
  gain,
  frameCount,
  onConnect,
  onDisconnect,
  onStartPreview,
  onStopPreview,
  onExposureChange,
  onGainChange,
  onApplySettings
}: CameraSettingsPanelProps) {
  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* 主内容区 - 左侧预览 + 右侧参数 */}
      <div className="flex-1 flex gap-4 p-4 overflow-hidden">
        
        {/* 左侧 - 相机预览区 */}
        <div className="flex-1 flex flex-col bg-[#252525] rounded-lg border border-[#3a3a3a] overflow-hidden">
          
          {/* 工具栏 */}
          <div className="px-4 py-3 border-b border-[#3a3a3a] flex items-center gap-2">
            <Button
              onClick={onConnect}
              disabled={isCameraConnected}
              className={`w-9 h-9 p-0 ${
                isCameraConnected
                  ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                  : 'bg-transparent text-gray-400 hover:bg-[#2a2a2a] hover:text-white'
              } border border-[#3a3a3a]`}
            >
              <Link className="w-4 h-4" />
            </Button>

            <Button
              onClick={onDisconnect}
              disabled={!isCameraConnected}
              className={`w-9 h-9 p-0 ${
                !isCameraConnected
                  ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                  : 'bg-transparent text-gray-400 hover:bg-[#2a2a2a] hover:text-white'
              } border border-[#3a3a3a]`}
            >
              <Unlink className="w-4 h-4" />
            </Button>

            <Separator orientation="vertical" className="h-6 bg-[#3a3a3a]" />

            <Button
              onClick={onStartPreview}
              disabled={!isCameraConnected || isPreviewing}
              className={`w-9 h-9 p-0 ${
                !isCameraConnected || isPreviewing
                  ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                  : 'bg-orange-500 text-white hover:bg-orange-600'
              }`}
            >
              <Video className="w-4 h-4" />
            </Button>

            <Button
              onClick={onStopPreview}
              disabled={!isPreviewing}
              className={`w-9 h-9 p-0 ${
                !isPreviewing
                  ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                  : 'bg-transparent text-red-400 hover:bg-red-500/10 border-red-500/50'
              } border border-[#3a3a3a]`}
            >
              <VideoOff className="w-4 h-4" />
            </Button>

            <Separator orientation="vertical" className="h-6 bg-[#3a3a3a]" />

            <Button
              disabled={!isPreviewing}
              className={`w-9 h-9 p-0 ${
                !isPreviewing
                  ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                  : 'bg-transparent text-gray-400 hover:bg-[#2a2a2a] hover:text-white'
              } border border-[#3a3a3a]`}
            >
              <ImageIcon className="w-4 h-4" />
            </Button>

            <Button
              disabled={!isPreviewing}
              className={`w-9 h-9 p-0 ${
                !isPreviewing
                  ? 'bg-gray-700 text-gray-500 cursor-not-allowed'
                  : 'bg-transparent text-gray-400 hover:bg-[#2a2a2a] hover:text-white'
              } border border-[#3a3a3a]`}
            >
              <Film className="w-4 h-4" />
            </Button>

            {/* 连接状态指示 */}
            <div className="ml-auto flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${
                isCameraConnected ? 'bg-green-500 animate-pulse' : 'bg-gray-600'
              }`}></div>
              <span className={`text-sm ${
                isCameraConnected ? 'text-green-400' : 'text-gray-500'
              }`}>
                {isCameraConnected ? '已连接' : '未连接'}
              </span>
            </div>
          </div>

          {/* 预览窗口 - 正方形 */}
          <div className="flex-1 p-6 flex items-center justify-center">
            <div className="aspect-square max-h-full max-w-full bg-black rounded-lg border-2 border-[#3a3a3a] flex items-center justify-center relative overflow-hidden">
              {isPreviewing ? (
                <>
                  {/* 模拟相机画面 */}
                  <div className="absolute inset-0 bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900"></div>
                  
                  {/* 十字线 */}
                  <svg className="absolute inset-0 w-full h-full pointer-events-none">
                    <line x1="50%" y1="0" x2="50%" y2="100%" stroke="#ff6b00" strokeWidth="1" strokeDasharray="5,5" opacity="0.5" />
                    <line x1="0" y1="50%" x2="100%" y2="50%" stroke="#ff6b00" strokeWidth="1" strokeDasharray="5,5" opacity="0.5" />
                    <circle cx="50%" cy="50%" r="40" fill="none" stroke="#ff6b00" strokeWidth="1.5" opacity="0.5" />
                  </svg>

                  {/* 预览标识 */}
                  <div className="absolute top-4 left-4 px-3 py-1 bg-red-500 rounded flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-white animate-pulse"></div>
                    <span className="text-white text-sm">LIVE</span>
                  </div>

                  {/* 帧信息 */}
                  <div className="absolute bottom-4 left-4 px-3 py-1 bg-black/50 rounded text-white text-sm">
                    Frame: {frameCount}
                  </div>
                </>
              ) : (
                <div className="text-center">
                  <Camera className="w-20 h-20 text-gray-600 mx-auto mb-3" />
                  <div className="text-gray-500">
                    {isCameraConnected ? '点击预览按钮开始' : '请先连接相机'}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* 右侧 - 参数面板 */}
        <div className="w-80 flex flex-col gap-4">
          
          {/* 相机参数 */}
          <div className="bg-[#252525] rounded-lg border border-[#3a3a3a] p-4">
            <h3 className="text-white mb-4 pb-2 border-b border-[#3a3a3a]">相机参数</h3>
            
            <div className="space-y-4">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <Label className="text-gray-400 text-sm">曝光时间 (μs)</Label>
                  <span className="text-white text-sm">{exposureTime}</span>
                </div>
                <Input
                  type="number"
                  value={exposureTime}
                  onChange={(e) => onExposureChange(Number(e.target.value))}
                  min="100"
                  max="100000"
                  step="100"
                  className="bg-[#1a1a1a] border-[#3a3a3a] text-white"
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-2">
                  <Label className="text-gray-400 text-sm">增益</Label>
                  <span className="text-white text-sm">{gain.toFixed(2)}</span>
                </div>
                <Input
                  type="number"
                  value={gain}
                  onChange={(e) => onGainChange(Number(e.target.value))}
                  min="0"
                  max="10"
                  step="0.1"
                  className="bg-[#1a1a1a] border-[#3a3a3a] text-white"
                />
              </div>

              <div>
                <Label className="text-gray-400 text-sm mb-2 block">分辨率</Label>
                <Select defaultValue="1920x1080">
                  <SelectTrigger className="bg-[#1a1a1a] border-[#3a3a3a] text-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-[#252525] border-[#3a3a3a]">
                    <SelectItem value="1920x1080" className="text-white focus:bg-orange-500/20">1920 × 1080</SelectItem>
                    <SelectItem value="1280x720" className="text-white focus:bg-orange-500/20">1280 × 720</SelectItem>
                    <SelectItem value="640x480" className="text-white focus:bg-orange-500/20">640 × 480</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label className="text-gray-400 text-sm mb-2 block">帧率 (FPS)</Label>
                <Input
                  type="number"
                  defaultValue="30"
                  className="bg-[#1a1a1a] border-[#3a3a3a] text-white"
                />
              </div>

              <div>
                <Label className="text-gray-400 text-sm mb-2 block">触发模式</Label>
                <Select defaultValue="continuous">
                  <SelectTrigger className="bg-[#1a1a1a] border-[#3a3a3a] text-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-[#252525] border-[#3a3a3a]">
                    <SelectItem value="continuous" className="text-white focus:bg-orange-500/20">连续采集</SelectItem>
                    <SelectItem value="software" className="text-white focus:bg-orange-500/20">软件触发</SelectItem>
                    <SelectItem value="hardware" className="text-white focus:bg-orange-500/20">硬件触发</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <Separator className="bg-[#3a3a3a]" />

              <Button
                onClick={onApplySettings}
                disabled={!isCameraConnected}
                className="w-full bg-orange-500 hover:bg-orange-600 text-white disabled:bg-gray-700 disabled:text-gray-500"
              >
                <Check className="w-4 h-4 mr-2" />
                应用设置
              </Button>
            </div>
          </div>

          {/* 图像处理 */}
          <div className="bg-[#252525] rounded-lg border border-[#3a3a3a] p-4">
            <h3 className="text-white mb-4 pb-2 border-b border-[#3a3a3a]">图像处理</h3>
            
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label className="text-gray-400 text-sm">自动白平衡</Label>
                <Switch className="data-[state=checked]:bg-orange-500" />
              </div>

              <div className="flex items-center justify-between">
                <Label className="text-gray-400 text-sm">降噪</Label>
                <Switch className="data-[state=checked]:bg-orange-500" defaultChecked />
              </div>

              <div className="flex items-center justify-between">
                <Label className="text-gray-400 text-sm">锐化</Label>
                <Switch className="data-[state=checked]:bg-orange-500" />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 底部统计信息栏 */}
      <div className="bg-[#252525] border-t border-[#3a3a3a] px-6 py-3 flex-shrink-0">
        <div className="grid grid-cols-6 gap-6">
          <div>
            <div className="text-gray-500 text-xs mb-1">设备型号</div>
            <div className="text-white text-sm">MV-CU120-10GM</div>
          </div>
          <div>
            <div className="text-gray-500 text-xs mb-1">设备温度</div>
            <div className="text-white text-sm">42°C</div>
          </div>
          <div>
            <div className="text-gray-500 text-xs mb-1">已采集帧数</div>
            <div className="text-white text-sm">{frameCount}</div>
          </div>
          <div>
            <div className="text-gray-500 text-xs mb-1">丢帧数</div>
            <div className="text-white text-sm">0</div>
          </div>
          <div>
            <div className="text-gray-500 text-xs mb-1">带宽占用</div>
            <div className="text-white text-sm">245 MB/s</div>
          </div>
          <div>
            <div className="text-gray-500 text-xs mb-1">触发频率</div>
            <div className="text-white text-sm">30 Hz</div>
          </div>
        </div>
      </div>
    </div>
  );
}

// 系统设置面板组件
interface SystemSettingsPanelProps {
  serverAddress: string;
  serverPort: string;
  imageSavePath: string;
  imageRetentionDays: string;
  logSavePath: string;
  logRetentionDays: string;
  onServerAddressChange: (value: string) => void;
  onServerPortChange: (value: string) => void;
  onImageSavePathChange: (value: string) => void;
  onImageRetentionDaysChange: (value: string) => void;
  onLogSavePathChange: (value: string) => void;
  onLogRetentionDaysChange: (value: string) => void;
}

function SystemSettingsPanel({
  serverAddress,
  serverPort,
  imageSavePath,
  imageRetentionDays,
  logSavePath,
  logRetentionDays,
  onServerAddressChange,
  onServerPortChange,
  onImageSavePathChange,
  onImageRetentionDaysChange,
  onLogSavePathChange,
  onLogRetentionDaysChange
}: SystemSettingsPanelProps) {
  
  const handleSaveSettings = () => {
    console.log('保存系统设置', {
      serverAddress,
      serverPort,
      imageSavePath,
      imageRetentionDays,
      logSavePath,
      logRetentionDays
    });
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* 标题栏 */}
      <div className="bg-[#252525] border-b border-[#3a3a3a] px-6 py-4 flex-shrink-0">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-white flex items-center gap-2">
              <Settings className="w-5 h-5 text-orange-500" />
              系统设置
            </h2>
            <p className="text-gray-400 text-sm mt-1">System Configuration</p>
          </div>
          <Button
            onClick={handleSaveSettings}
            className="bg-orange-500 hover:bg-orange-600 text-white"
          >
            <Check className="w-4 h-4 mr-2" />
            保存配置
          </Button>
        </div>
      </div>

      {/* 表单内容区 */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-4xl mx-auto space-y-6">
          
          {/* 服务器配置 */}
          <div className="bg-[#252525] rounded-lg border border-[#3a3a3a] p-6">
            <div className="flex items-center gap-2 mb-4 pb-3 border-b border-[#3a3a3a]">
              <Server className="w-5 h-5 text-orange-500" />
              <h3 className="text-white">中心服务器配置</h3>
            </div>
            
            <div className="grid grid-cols-2 gap-6">
              <div>
                <Label className="text-gray-400 text-sm mb-2 block">服务器地址</Label>
                <Input
                  value={serverAddress}
                  onChange={(e) => onServerAddressChange(e.target.value)}
                  placeholder="192.168.1.100"
                  className="bg-[#1a1a1a] border-[#3a3a3a] text-white placeholder:text-gray-600"
                />
                <p className="text-gray-500 text-xs mt-1">中心数据服务器的IP地址</p>
              </div>
              
              <div>
                <Label className="text-gray-400 text-sm mb-2 block">服务器端口</Label>
                <Input
                  value={serverPort}
                  onChange={(e) => onServerPortChange(e.target.value)}
                  placeholder="8080"
                  className="bg-[#1a1a1a] border-[#3a3a3a] text-white placeholder:text-gray-600"
                />
                <p className="text-gray-500 text-xs mt-1">服务监听端口号</p>
              </div>
            </div>
          </div>

          {/* 图像存储配置 */}
          <div className="bg-[#252525] rounded-lg border border-[#3a3a3a] p-6">
            <div className="flex items-center gap-2 mb-4 pb-3 border-b border-[#3a3a3a]">
              <ImageIcon className="w-5 h-5 text-orange-500" />
              <h3 className="text-white">图像存储配置</h3>
            </div>
            
            <div className="space-y-4">
              <div>
                <Label className="text-gray-400 text-sm mb-2 block">图像保存位置</Label>
                <div className="flex gap-2">
                  <Input
                    value={imageSavePath}
                    onChange={(e) => onImageSavePathChange(e.target.value)}
                    placeholder="C:\VisionData\Images"
                    className="flex-1 bg-[#1a1a1a] border-[#3a3a3a] text-white placeholder:text-gray-600"
                  />
                  <Button
                    className="bg-transparent border border-[#3a3a3a] text-gray-400 hover:bg-[#2a2a2a] hover:text-white"
                  >
                    <FolderOpen className="w-4 h-4" />
                  </Button>
                </div>
                <p className="text-gray-500 text-xs mt-1">采集图像的本地存储路径</p>
              </div>

              <div>
                <Label className="text-gray-400 text-sm mb-2 block">图像保留时间（天）</Label>
                <Input
                  value={imageRetentionDays}
                  onChange={(e) => onImageRetentionDaysChange(e.target.value)}
                  type="number"
                  placeholder="30"
                  className="bg-[#1a1a1a] border-[#3a3a3a] text-white placeholder:text-gray-600"
                />
                <p className="text-gray-500 text-xs mt-1">超过此天数的图像将被自动清理</p>
              </div>
            </div>
          </div>

          {/* 日志存储配置 */}
          <div className="bg-[#252525] rounded-lg border border-[#3a3a3a] p-6">
            <div className="flex items-center gap-2 mb-4 pb-3 border-b border-[#3a3a3a]">
              <FileText className="w-5 h-5 text-orange-500" />
              <h3 className="text-white">日志存储配置</h3>
            </div>
            
            <div className="space-y-4">
              <div>
                <Label className="text-gray-400 text-sm mb-2 block">日志保存位置</Label>
                <div className="flex gap-2">
                  <Input
                    value={logSavePath}
                    onChange={(e) => onLogSavePathChange(e.target.value)}
                    placeholder="C:\VisionData\Logs"
                    className="flex-1 bg-[#1a1a1a] border-[#3a3a3a] text-white placeholder:text-gray-600"
                  />
                  <Button
                    className="bg-transparent border border-[#3a3a3a] text-gray-400 hover:bg-[#2a2a2a] hover:text-white"
                  >
                    <FolderOpen className="w-4 h-4" />
                  </Button>
                </div>
                <p className="text-gray-500 text-xs mt-1">系统日志的本地存储路径</p>
              </div>

              <div>
                <Label className="text-gray-400 text-sm mb-2 block">日志保留时间（天）</Label>
                <Input
                  value={logRetentionDays}
                  onChange={(e) => onLogRetentionDaysChange(e.target.value)}
                  type="number"
                  placeholder="90"
                  className="bg-[#1a1a1a] border-[#3a3a3a] text-white placeholder:text-gray-600"
                />
                <p className="text-gray-500 text-xs mt-1">超过此天数的日志将被自动清理</p>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}

// 模型管理面板组件
function ModelManagementPanel() {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState('all');

  // 模拟模型数据
  const models = [
    {
      id: 1,
      name: 'Edge Detection Standard',
      type: 'opencv',
      version: 'v2.1.0',
      description: 'Canny边缘检测算法，用于零件边缘识别',
      size: '1.2 MB',
      lastUpdated: '2024-11-05',
      status: 'active'
    },
    {
      id: 2,
      name: 'Component Position Check',
      type: 'opencv',
      version: 'v1.8.3',
      description: '基于模板匹配的零件位置检测',
      size: '850 KB',
      lastUpdated: '2024-11-01',
      status: 'active'
    },
    {
      id: 3,
      name: 'PCB Defect Detection',
      type: 'yolo',
      version: 'v5.0.2',
      description: 'YOLOv8缺陷检测模型，识别PCB焊接缺陷',
      size: '45.6 MB',
      lastUpdated: '2024-11-03',
      status: 'active'
    },
    {
      id: 4,
      name: 'Screw Detection',
      type: 'yolo',
      version: 'v3.2.1',
      description: 'YOLOv5螺丝检测模型，验证螺丝安装',
      size: '28.3 MB',
      lastUpdated: '2024-10-28',
      status: 'active'
    },
    {
      id: 5,
      name: 'QR Code Reader',
      type: 'opencv',
      version: 'v1.5.0',
      description: 'QR码识别与解码算法',
      size: '600 KB',
      lastUpdated: '2024-10-25',
      status: 'inactive'
    },
    {
      id: 6,
      name: 'Assembly Classification',
      type: 'yolo',
      version: 'v4.1.0',
      description: 'YOLOv7装配状态分类模型',
      size: '52.1 MB',
      lastUpdated: '2024-11-02',
      status: 'active'
    }
  ];

  const filteredModels = models.filter(model => {
    const matchesSearch = model.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         model.description.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesType = filterType === 'all' || model.type === filterType;
    return matchesSearch && matchesType;
  });

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* 标题栏 */}
      <div className="bg-[#252525] border-b border-[#3a3a3a] px-6 py-4 flex-shrink-0">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-white flex items-center gap-2">
              <Database className="w-5 h-5 text-orange-500" />
              模型管理
            </h2>
            <p className="text-gray-400 text-sm mt-1">Model Management - {filteredModels.length} 个模型已缓存</p>
          </div>
          <div className="flex items-center gap-2">
            <Button className="bg-transparent border border-[#3a3a3a] text-gray-400 hover:bg-[#2a2a2a] hover:text-white">
              <Download className="w-4 h-4 mr-2" />
              从服务器下载
            </Button>
            <Button className="bg-orange-500 hover:bg-orange-600 text-white">
              <Upload className="w-4 h-4 mr-2" />
              上传模型
            </Button>
          </div>
        </div>
      </div>

      {/* 搜索和筛选栏 */}
      <div className="bg-[#1f1f1f] border-b border-[#3a3a3a] px-6 py-3 flex-shrink-0">
        <div className="flex items-center gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <Input
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="搜索模型名称或描述..."
              className="pl-10 bg-[#1a1a1a] border-[#3a3a3a] text-white placeholder:text-gray-600"
            />
          </div>
          <Select value={filterType} onValueChange={setFilterType}>
            <SelectTrigger className="w-48 bg-[#1a1a1a] border-[#3a3a3a] text-white">
              <Filter className="w-4 h-4 mr-2" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-[#252525] border-[#3a3a3a]">
              <SelectItem value="all" className="text-white">所有��型</SelectItem>
              <SelectItem value="opencv" className="text-white">OpenCV传统</SelectItem>
              <SelectItem value="yolo" className="text-white">深度学习</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* 模型卡片网格 */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
          {filteredModels.map(model => (
            <Card key={model.id} className="bg-[#252525] border-[#3a3a3a] hover:border-orange-500/50 transition-colors">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    {model.type === 'opencv' ? (
                      <div className="w-10 h-10 rounded bg-blue-500/10 flex items-center justify-center">
                        <Cpu className="w-5 h-5 text-blue-400" />
                      </div>
                    ) : (
                      <div className="w-10 h-10 rounded bg-purple-500/10 flex items-center justify-center">
                        <Brain className="w-5 h-5 text-purple-400" />
                      </div>
                    )}
                    <div>
                      <CardTitle className="text-white text-sm">{model.name}</CardTitle>
                      <CardDescription className="text-xs text-gray-500">{model.version}</CardDescription>
                    </div>
                  </div>
                  <Badge 
                    className={`${
                      model.status === 'active' 
                        ? 'bg-green-500/10 text-green-400 border-green-500/30' 
                        : 'bg-gray-500/10 text-gray-400 border-gray-500/30'
                    }`}
                  >
                    {model.status === 'active' ? '启用' : '未用'}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-gray-400 text-sm mb-4">{model.description}</p>
                
                <div className="grid grid-cols-2 gap-2 mb-4">
                  <div className="bg-[#1a1a1a] rounded p-2">
                    <div className="text-gray-500 text-xs">类型</div>
                    <div className="text-white text-sm">
                      {model.type === 'opencv' ? 'OpenCV' : 'YOLO'}
                    </div>
                  </div>
                  <div className="bg-[#1a1a1a] rounded p-2">
                    <div className="text-gray-500 text-xs">大小</div>
                    <div className="text-white text-sm">{model.size}</div>
                  </div>
                  <div className="bg-[#1a1a1a] rounded p-2 col-span-2">
                    <div className="text-gray-500 text-xs">更新时间</div>
                    <div className="text-white text-sm">{model.lastUpdated}</div>
                  </div>
                </div>

                <div className="flex gap-2">
                  <Button className="flex-1 bg-transparent border border-[#3a3a3a] text-gray-400 hover:bg-[#2a2a2a] hover:text-white h-8">
                    <Eye className="w-3 h-3 mr-1" />
                    查看
                  </Button>
                  <Button className="flex-1 bg-orange-500 hover:bg-orange-600 text-white h-8">
                    <Download className="w-3 h-3 mr-1" />
                    更新
                  </Button>
                  <Button className="bg-transparent border border-red-500/50 text-red-400 hover:bg-red-500/10 h-8 w-8 p-0">
                    <Trash2 className="w-3 h-3" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}

// 工艺信息面板组件
function ProcessInfoPanel() {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState('all');

  // 模拟工艺过程文件数据
  const processes = [
    {
      id: 1,
      name: 'ME-ASM-2024-001',
      title: '机械底座装配工艺',
      type: 'mechanical',
      version: 'v3.2',
      steps: 12,
      models: ['Edge Detection Standard', 'Screw Detection'],
      status: 'active',
      lastModified: '2024-11-05'
    },
    {
      id: 2,
      name: 'PCB-ASM-2024-015',
      title: '主控板PCB装配工艺',
      type: 'pcb',
      version: 'v2.8',
      steps: 8,
      models: ['PCB Defect Detection', 'Component Position Check'],
      status: 'active',
      lastModified: '2024-11-03'
    },
    {
      id: 3,
      name: 'PKG-STD-2024-003',
      title: '标准包装工艺流程',
      type: 'packaging',
      version: 'v1.5',
      steps: 5,
      models: ['QR Code Reader', 'Assembly Classification'],
      status: 'active',
      lastModified: '2024-10-28'
    },
    {
      id: 4,
      name: 'ME-ASM-2024-002',
      title: '外壳组件装配工艺',
      type: 'mechanical',
      version: 'v2.1',
      steps: 10,
      models: ['Edge Detection Standard', 'Component Position Check'],
      status: 'draft',
      lastModified: '2024-11-01'
    },
    {
      id: 5,
      name: 'PCB-ASM-2024-016',
      title: '接口板PCB装配工艺',
      type: 'pcb',
      version: 'v1.9',
      steps: 6,
      models: ['PCB Defect Detection'],
      status: 'active',
      lastModified: '2024-10-30'
    }
  ];

  const typeLabels: Record<string, { label: string; color: string }> = {
    mechanical: { label: '机械安装', color: 'bg-blue-500/10 text-blue-400 border-blue-500/30' },
    pcb: { label: 'PCB安装', color: 'bg-green-500/10 text-green-400 border-green-500/30' },
    packaging: { label: '包装', color: 'bg-purple-500/10 text-purple-400 border-purple-500/30' }
  };

  const filteredProcesses = processes.filter(process => {
    const matchesSearch = process.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         process.title.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesType = filterType === 'all' || process.type === filterType;
    return matchesSearch && matchesType;
  });

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* 标题栏 */}
      <div className="bg-[#252525] border-b border-[#3a3a3a] px-6 py-4 flex-shrink-0">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-white flex items-center gap-2">
              <FileText className="w-5 h-5 text-orange-500" />
              工艺信息
            </h2>
            <p className="text-gray-400 text-sm mt-1">Process Information - {filteredProcesses.length} 个工艺文件</p>
          </div>
          <div className="flex items-center gap-2">
            <Button className="bg-transparent border border-[#3a3a3a] text-gray-400 hover:bg-[#2a2a2a] hover:text-white">
              <Download className="w-4 h-4 mr-2" />
              从服务器同步
            </Button>
            <Button className="bg-orange-500 hover:bg-orange-600 text-white">
              <Upload className="w-4 h-4 mr-2" />
              创建工艺
            </Button>
          </div>
        </div>
      </div>

      {/* 搜索和筛选栏 */}
      <div className="bg-[#1f1f1f] border-b border-[#3a3a3a] px-6 py-3 flex-shrink-0">
        <div className="flex items-center gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <Input
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="搜索工艺编号或名称..."
              className="pl-10 bg-[#1a1a1a] border-[#3a3a3a] text-white placeholder:text-gray-600"
            />
          </div>
          <Select value={filterType} onValueChange={setFilterType}>
            <SelectTrigger className="w-48 bg-[#1a1a1a] border-[#3a3a3a] text-white">
              <Filter className="w-4 h-4 mr-2" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-[#252525] border-[#3a3a3a]">
              <SelectItem value="all" className="text-white">所有类型</SelectItem>
              <SelectItem value="mechanical" className="text-white">机械安装</SelectItem>
              <SelectItem value="pcb" className="text-white">PCB安装</SelectItem>
              <SelectItem value="packaging" className="text-white">包装</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* 工艺卡片列表 */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-5xl mx-auto space-y-4">
          {filteredProcesses.map(process => (
            <Card key={process.id} className="bg-[#252525] border-[#3a3a3a] hover:border-orange-500/50 transition-colors">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <div className="w-10 h-10 rounded bg-orange-500/10 flex items-center justify-center">
                        {process.type === 'mechanical' ? (
                          <Box className="w-5 h-5 text-orange-400" />
                        ) : process.type === 'pcb' ? (
                          <Cpu className="w-5 h-5 text-orange-400" />
                        ) : (
                          <Package className="w-5 h-5 text-orange-400" />
                        )}
                      </div>
                      <div className="flex-1">
                        <CardTitle className="text-white">{process.title}</CardTitle>
                        <CardDescription className="text-gray-500">{process.name} · {process.version}</CardDescription>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge className={typeLabels[process.type].color}>
                          {typeLabels[process.type].label}
                        </Badge>
                        <Badge 
                          className={`${
                            process.status === 'active' 
                              ? 'bg-green-500/10 text-green-400 border-green-500/30' 
                              : 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30'
                          }`}
                        >
                          {process.status === 'active' ? '已发布' : '草稿'}
                        </Badge>
                      </div>
                    </div>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-4 gap-4 mb-4">
                  <div className="bg-[#1a1a1a] rounded p-3">
                    <div className="text-gray-500 text-xs mb-1">工艺步骤</div>
                    <div className="text-white">{process.steps} 步</div>
                  </div>
                  <div className="bg-[#1a1a1a] rounded p-3">
                    <div className="text-gray-500 text-xs mb-1">使用模型</div>
                    <div className="text-white">{process.models.length} 个</div>
                  </div>
                  <div className="bg-[#1a1a1a] rounded p-3 col-span-2">
                    <div className="text-gray-500 text-xs mb-1">最后修改</div>
                    <div className="text-white">{process.lastModified}</div>
                  </div>
                </div>

                <div className="mb-4">
                  <div className="text-gray-400 text-sm mb-2">关联模型：</div>
                  <div className="flex flex-wrap gap-2">
                    {process.models.map((model, idx) => (
                      <Badge key={idx} className="bg-[#1a1a1a] text-gray-300 border-[#3a3a3a]">
                        {model}
                      </Badge>
                    ))}
                  </div>
                </div>

                <div className="flex gap-2">
                  <Button className="flex-1 bg-transparent border border-[#3a3a3a] text-gray-400 hover:bg-[#2a2a2a] hover:text-white">
                    <Eye className="w-4 h-4 mr-2" />
                    查看详情
                  </Button>
                  <Button className="flex-1 bg-orange-500 hover:bg-orange-600 text-white">
                    <Play className="w-4 h-4 mr-2" />
                    启动工艺
                  </Button>
                  <Button className="bg-transparent border border-[#3a3a3a] text-gray-400 hover:bg-[#2a2a2a] hover:text-white">
                    编辑
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}

// 工作记录面板组件
function WorkRecordsPanel() {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');

  // 模拟工作记录数据
  const records = [
    {
      id: 1,
      recordId: 'REC-2024110701234',
      processName: 'ME-ASM-2024-001',
      processTitle: '机械底座装配工艺',
      productSN: 'SN20241107001',
      orderNo: 'ORD-2024-1105',
      operator: '张三',
      workstation: 'A01',
      status: 'ok',
      startTime: '2024-11-07 09:15:23',
      endTime: '2024-11-07 09:28:45',
      duration: '13min 22s',
      defects: []
    },
    {
      id: 2,
      recordId: 'REC-2024110701235',
      processName: 'PCB-ASM-2024-015',
      processTitle: '主控板PCB装配工艺',
      productSN: 'SN20241107002',
      orderNo: 'ORD-2024-1105',
      operator: '李四',
      workstation: 'B02',
      status: 'ng',
      startTime: '2024-11-07 09:30:15',
      endTime: '2024-11-07 09:42:30',
      duration: '12min 15s',
      defects: ['焊点缺失', 'PCB位置偏移']
    },
    {
      id: 3,
      recordId: 'REC-2024110701236',
      processName: 'PKG-STD-2024-003',
      processTitle: '标准包装工艺流程',
      productSN: 'SN20241107003',
      orderNo: 'ORD-2024-1106',
      operator: '王五',
      workstation: 'C01',
      status: 'conditional',
      startTime: '2024-11-07 10:05:00',
      endTime: '2024-11-07 10:12:18',
      duration: '7min 18s',
      defects: ['标签轻微歪斜']
    },
    {
      id: 4,
      recordId: 'REC-2024110701237',
      processName: 'ME-ASM-2024-001',
      processTitle: '机械底座装配工艺',
      productSN: 'SN20241107004',
      orderNo: 'ORD-2024-1105',
      operator: '张三',
      workstation: 'A01',
      status: 'ok',
      startTime: '2024-11-07 10:30:45',
      endTime: '2024-11-07 10:43:20',
      duration: '12min 35s',
      defects: []
    },
    {
      id: 5,
      recordId: 'REC-2024110701238',
      processName: 'PCB-ASM-2024-016',
      processTitle: '接口板PCB装配工艺',
      productSN: 'SN20241107005',
      orderNo: 'ORD-2024-1106',
      operator: '赵六',
      workstation: 'B03',
      status: 'ok',
      startTime: '2024-11-07 11:00:10',
      endTime: '2024-11-07 11:08:55',
      duration: '8min 45s',
      defects: []
    }
  ];

  const statusLabels: Record<string, { label: string; icon: any; className: string }> = {
    ok: { 
      label: 'OK', 
      icon: CheckCircle,
      className: 'bg-green-500/10 text-green-400 border-green-500/30' 
    },
    ng: { 
      label: 'NG', 
      icon: XCircle,
      className: 'bg-red-500/10 text-red-400 border-red-500/30' 
    },
    conditional: { 
      label: '条件通过', 
      icon: AlertCircle,
      className: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30' 
    }
  };

  const filteredRecords = records.filter(record => {
    const matchesSearch = record.recordId.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         record.productSN.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         record.processTitle.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = filterStatus === 'all' || record.status === filterStatus;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* 标题栏 */}
      <div className="bg-[#252525] border-b border-[#3a3a3a] px-6 py-4 flex-shrink-0">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-white flex items-center gap-2">
              <ClipboardList className="w-5 h-5 text-orange-500" />
              工作记录
            </h2>
            <p className="text-gray-400 text-sm mt-1">Work Records - {filteredRecords.length} 条记录</p>
          </div>
          <div className="flex items-center gap-2">
            <Button className="bg-transparent border border-[#3a3a3a] text-gray-400 hover:bg-[#2a2a2a] hover:text-white">
              <Calendar className="w-4 h-4 mr-2" />
              选择日期
            </Button>
            <Button className="bg-orange-500 hover:bg-orange-600 text-white">
              <Download className="w-4 h-4 mr-2" />
              导出报表
            </Button>
          </div>
        </div>
      </div>

      {/* 搜索和筛选栏 */}
      <div className="bg-[#1f1f1f] border-b border-[#3a3a3a] px-6 py-3 flex-shrink-0">
        <div className="flex items-center gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
            <Input
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="搜索记录编号、产品SN或工艺名称..."
              className="pl-10 bg-[#1a1a1a] border-[#3a3a3a] text-white placeholder:text-gray-600"
            />
          </div>
          <Select value={filterStatus} onValueChange={setFilterStatus}>
            <SelectTrigger className="w-48 bg-[#1a1a1a] border-[#3a3a3a] text-white">
              <Filter className="w-4 h-4 mr-2" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="bg-[#252525] border-[#3a3a3a]">
              <SelectItem value="all" className="text-white">所有状态</SelectItem>
              <SelectItem value="ok" className="text-white">OK</SelectItem>
              <SelectItem value="ng" className="text-white">NG</SelectItem>
              <SelectItem value="conditional" className="text-white">条件通过</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* 记录表格 */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="bg-[#252525] border border-[#3a3a3a] rounded-lg overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="border-[#3a3a3a] hover:bg-[#2a2a2a]">
                <TableHead className="text-gray-400">记录编号</TableHead>
                <TableHead className="text-gray-400">产品SN</TableHead>
                <TableHead className="text-gray-400">工艺名称</TableHead>
                <TableHead className="text-gray-400">操作员</TableHead>
                <TableHead className="text-gray-400">工位</TableHead>
                <TableHead className="text-gray-400">耗时</TableHead>
                <TableHead className="text-gray-400">状态</TableHead>
                <TableHead className="text-gray-400">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredRecords.map(record => {
                const StatusIcon = statusLabels[record.status].icon;
                return (
                  <TableRow key={record.id} className="border-[#3a3a3a] hover:bg-[#2a2a2a]">
                    <TableCell className="text-white">{record.recordId}</TableCell>
                    <TableCell className="text-white">{record.productSN}</TableCell>
                    <TableCell>
                      <div className="text-white">{record.processTitle}</div>
                      <div className="text-gray-500 text-xs">{record.processName}</div>
                    </TableCell>
                    <TableCell className="text-white">{record.operator}</TableCell>
                    <TableCell>
                      <Badge className="bg-orange-500/10 text-orange-400 border-orange-500/30">
                        {record.workstation}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-white">{record.duration}</TableCell>
                    <TableCell>
                      <Badge className={`flex items-center gap-1 w-fit ${statusLabels[record.status].className}`}>
                        <StatusIcon className="w-3 h-3" />
                        {statusLabels[record.status].label}
                      </Badge>
                      {record.defects.length > 0 && (
                        <div className="text-xs text-red-400 mt-1">
                          {record.defects.join(', ')}
                        </div>
                      )}
                    </TableCell>
                    <TableCell>
                      <Button className="bg-transparent border border-[#3a3a3a] text-gray-400 hover:bg-[#2a2a2a] hover:text-white h-8">
                        <Eye className="w-3 h-3 mr-1" />
                        详情
                      </Button>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      </div>
    </div>
  );
}
